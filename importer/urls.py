from django.urls import path
from . import views

urlpatterns = [
    path('groups/<int:group_id>/import/', views.CSVImportView.as_view(), name='csv-import'),
    path('import/<int:session_id>/report/', views.ImportReportView.as_view(), name='import-report'),
]