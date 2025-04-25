import json
import logging

import requests
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger('scout_agent')


class LeadDetailsService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.tavily_api_key = settings.TAVILY_API_KEY

    def generate_queries(self, company_name):
        return {
            "industry_keywords": f"{company_name} 산업 분야",
            "homepage_url": f"{company_name} 공식 홈페이지",
            "key_executives": f"{company_name} CEO",
            "company_address": f"{company_name} 회사 주소",
            "company_summary": f"{company_name} 회사 설명",
            "target_customers": f"{company_name} 주요 타겟 고객층",
            "competitors": f"{company_name} 주요 경쟁사",
            "strengths": f"{company_name} 강점",
            "risk_factors": f"{company_name} 위험 요인",
            "recent_trends": f"{company_name} 최근 동향",
            "financial_info": f"{company_name} 재무 정보",
            "founded_date": f"{company_name} 설립일",
            "logo_url": f"{company_name} 로고 이미지 url",
            "competitive_field" : f"{company_name} "
        }

    def search_tavily(self, query, num_results=3):
        url = "https://api.tavily.com/search"
        headers = {
            "Authorization": f"Bearer {self.tavily_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "search_depth": "basic"
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            results = response.json().get("results", [])[:num_results]
            return [
                {"url": r.get("url"), "title": r.get("title"), "content": r.get("content", "")}
                for r in results if "content" in r and "url" in r
            ]
        except Exception as e:
            print(f"⚠️ Tavily 검색 실패: {e}")
            return []

    def get_latest_news_urls(self, company_name: str, count=3):
        query = f"{company_name} 최신 뉴스"
        url = "https://api.tavily.com/search"
        headers = {
            "Authorization": f"Bearer {self.tavily_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "search_depth": "basic"
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            results = response.json().get("results", [])[:count]
            return [
                {
                    "title": r.get("title", "제목 없음"),
                    "url": r.get("url", "")
                }
                for r in results
            ]
        except Exception as e:
            print(f"❌ 최신 뉴스 검색 실패: {e}")
            return []

    def extract_info(self, company_name):
        queries = self.generate_queries(company_name)
        extracted_info = {}

        for field, query in queries.items():
            sources = self.search_tavily(query)
            if not sources:
                print(f"⚠️ {field} 관련된 content 없음 (패스)")
                continue

            contents = [s["content"] for s in sources]
            urls = [
                {
                    "title": s.get("title", "제목 없음"),
                    "url": s.get("url", "")
                } for s in sources
            ]

            combined_content = "\n\n".join(contents)

            prompt = f"""
            당신은 회사 분석 전문가입니다. '{company_name}'의 '{field}' 항목만 다음 규칙에 따라 **한 가지** JSON 값으로 반환하세요.

            - 만약 field가 "company_summary"라면 → **2~3문장** 자유 서술
            - 만약 field가 "industry_keywords"라면 → **상위 5개** 키워드 리스트
            - 만약 field가 "target_customers"라면 → **3~5개** 키워드 리스트
            - 만약 field가 "financial_info"라면 → 연도:금액 쌍의 **객체**
            - 만약 field가 "recent_trends"라면 → **3~5개** 키워드 리스트
            - 만약 field가 "competitors"라면 → 경쟁사: 주요 경쟁 분야 쌍의 **객체**
            - 만약 field가 "strengths"라면 → **3~5개** 리스트
            - 만약 field가 "risk_factors"라면 → **3~5개** 리스트
            - 만약 filed가 ""
            - 기타(founded_date, company_address, homepage_url, key_executives, logo_url) → **단일 문자열** (또는 리스트)

            회사명: "{company_name}"
            요청 항목: "{field}"

            ### 참고 텍스트:
            {combined_content}

            ### 출력은 오직 아래처럼 JSON만:
            ```json
            {{
            "{field}": ...  // 위 규칙에 맞춘 값
            }}

            """

            try:
                completion = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "You are a structured data extractor."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                field_result = json.loads(completion.choices[0].message.content)
                extracted_info[field] = field_result[field]
                extracted_info[f"{field}_sources"] = urls
            except Exception as e:
                print(f"❌ LLM 추출 실패 [{field}]: {e}")
                continue

        # 최신 뉴스 URL 리스트 추가
        # "url" 변수명 변경 가능
        extracted_info["news"] = self.get_latest_news_urls(company_name)
        extracted_info["company_name"] = company_name

        print(json.dumps(extracted_info, indent=2, ensure_ascii=False))

        return extracted_info
