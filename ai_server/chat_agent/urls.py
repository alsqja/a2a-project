from django.urls import path
from .views import ChatAgentView, PDFAnalysisView, A2aChatView

urlpatterns = [
    path('analyze-pdf', PDFAnalysisView.as_view(), name='analyze_pdf'),
    path('chats', ChatAgentView.as_view(), name='chat_agent'),
    path('agents/chats', A2aChatView.as_view(), name='agent_chats'),
]