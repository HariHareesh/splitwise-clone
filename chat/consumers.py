import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from users.models import User
from .models import Message
from groups.models import Group, GroupMember
from expenses.models import Expense


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = await self.get_user_from_token()
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close()
            return

        self.room_type = self.scope['url_route']['kwargs'].get('room_type')
        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        self.room_group_name = f"chat_{self.room_type}_{self.room_id}"

        # Verify membership
        is_member = await self.check_membership()
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content', '').strip()
        if not content:
            return

        message = await self.save_message(content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': {
                        'id': self.user.id,
                        'username': self.user.username,
                        'full_name': self.user.full_name,
                        'avatar_url': self.user.avatar_url,
                    },
                    'created_at': message.created_at.isoformat(),
                }
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def get_user_from_token(self):
        try:
            token = None
            query_string = self.scope.get('query_string', b'').decode()
            for param in query_string.split('&'):
                if param.startswith('token='):
                    token = param.split('=', 1)[1]
                    break
            if not token:
                return None
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def check_membership(self):
        try:
            if self.room_type == 'group':
                return GroupMember.objects.filter(
                    group_id=self.room_id,
                    user=self.user,
                    is_active=True
                ).exists()
            elif self.room_type == 'expense':
                expense = Expense.objects.get(id=self.room_id)
                return GroupMember.objects.filter(
                    group=expense.group,
                    user=self.user,
                    is_active=True
                ).exists()
            return False
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, content):
        kwargs = {'sender': self.user, 'content': content}
        if self.room_type == 'group':
            kwargs['group_id'] = self.room_id
        elif self.room_type == 'expense':
            kwargs['expense_id'] = self.room_id
        return Message.objects.create(**kwargs)