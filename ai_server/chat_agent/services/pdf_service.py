import urllib.request
import fitz  # PyMuPDF

from django.conf import settings
from django.db import transaction
from openai import OpenAI
import tempfile
import os

from chat_agent.models import CompanyFile


class PDFAnalysisService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def analyze_company_pdf(self, file_id):
        """
        PDF 파일을 분석하여 회사 정보를 추출하고 DB에 저장합니다.

        Returns:
            dict: 추출된 회사 정보
        """
        try:
            company_file = CompanyFile.objects.get(id=file_id)
            # PDF 텍스트 추출
            extracted_text = self._extract_text_from_pdf(company_file.url)
            if not extracted_text:
                print("PDF에서 텍스트를 추출할 수 없습니다.")
                return {}

            # OpenAI를 사용하여 텍스트에서 회사 정보 추출
            company_info = self._extract_company_info_with_ai(extracted_text, company_file.company.company_name)

            with transaction.atomic():
                CompanyFile.objects.update_or_create(
                    id=file_id,
                    defaults={
                        "summary": company_info
                    }
                )

            return company_info

        except Exception as e:
            print(f"PDF 분석 중 오류 발생: {e}")
            return {}

    def _extract_text_from_pdf(self, pdf_path):
        """
        PyMuPDF를 사용하여 PDF에서 텍스트를 추출합니다.
        """
        try:
            downloaded_path = self._download_pdf(pdf_path)
            text = ""
            # PDF 파일 열기
            with fitz.open(downloaded_path) as doc:
                # 각 페이지의 텍스트 추출
                for page in doc:
                    text += page.get_text()

            # 텍스트가 너무 길면 잘라내기 (OpenAI API 제한 고려)
            max_length = 15000
            if len(text) > max_length:
                print(f"PDF 텍스트가 너무 길어 {max_length}자로 제한합니다.")
                text = text[:max_length]

            os.remove(downloaded_path)

            return text
        except Exception as e:
            print(f"PDF 텍스트 추출 오류: {e}")
            return ""

    def _download_pdf(self, url):
        """URL에서 PDF 파일을 다운로드하고 임시 파일 경로를 반환합니다."""
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_path = temp_file.name

            # PDF 다운로드
            urllib.request.urlretrieve(url, temp_path)
            print(f"PDF 다운로드 완료: {url}")
            return temp_path
        except Exception as e:
            print(f"PDF 다운로드 오류: {e}")
            return None

    def _extract_company_info_with_ai(self, text, company_name):
        """
        OpenAI API를 사용하여 PDF 텍스트에서 회사 정보를 추출합니다.
        """
        try:
            prompt = f"""
                당신은 회사 분석 전문가입니다. 아래 제공된 PDF에서 추출한 텍스트를 분석하여 "{company_name}" 회사에 대한 상세 정보를 추출해주세요.

                seller, buyer 의 입장에서 필요한 정보들을 찾아 문자열로 반환해주세요:

                텍스트에서 명확하게 확인할 수 없는 정보는 생략하세요. 
                특히 매출액이나 투자금액 등 수치는 확실한 숫자만 포함하고 추측하지 마세요.

                분석할 PDF 텍스트:
                {text}

                """

            # GPT-4 API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system",
                     "content": "You are a company analysis expert that extracts structured information from PDF documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )

            # JSON 응답 추출 및 파싱
            result = response.choices[0].message.content.strip()

            return result

        except Exception as e:
            print(f"AI를 사용한 정보 추출 오류: {e}")
            return {}
