from django.urls import path
from .views import ChatAgentView, PDFAnalysisView, A2aChatView, ChatSummaryView, LeadDataView

urlpatterns = [
    path('analyze-pdf', PDFAnalysisView.as_view(), name='analyze_pdf'),
    path('chats', ChatAgentView.as_view(), name='chat_agent'),
    path('leads/<int:lead_id>/agents/chats', A2aChatView.as_view(), name='agent_chats'),
    path('rooms/<int:room_id>/summary', ChatSummaryView.as_view(), name='chat_agent_summary'),
    path('leads/details', LeadDataView.as_view(), name='leads_details'),
]