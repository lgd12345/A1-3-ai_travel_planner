import json
import os
from datetime import datetime
from pathlib import Path

import requests

from dotenv import load_dotenv
from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# =========================================================
# 1. Project / Environment
# =========================================================

# api/index.py 기준으로 부모의 부모가 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 로컬 개발에서는 프로젝트 루트의 .env 로드
# Vercel 배포에서는 Vercel Environment Variables를 사용
load_dotenv(PROJECT_ROOT / ".env")


# =========================================================
# 2. FastAPI Application
# =========================================================

app = FastAPI(
    title="TripAI API",
    version="1.0.0",
)


# =========================================================
# 3. Static Frontend
# =========================================================

# CSS
css_directory = PROJECT_ROOT / "css"

if css_directory.exists():
    app.mount(
        "/css",
        StaticFiles(
            directory=str(css_directory)
        ),
        name="css",
    )


# JavaScript
js_directory = PROJECT_ROOT / "js"

if js_directory.exists():
    app.mount(
        "/js",
        StaticFiles(
            directory=str(js_directory)
        ),
        name="js",
    )


# Images
images_directory = PROJECT_ROOT / "images"

if images_directory.exists():
    app.mount(
        "/images",
        StaticFiles(
            directory=str(images_directory)
        ),
        name="images",
    )


# =========================================================
# 4. External API Configuration
# =========================================================

NAITO_URL = (
    "https://copa.codyssey.kr/v1/chat/completions"
)

NAITO_MODEL = "gpt-5.5"

KAKAO_LOCAL_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)

REQUEST_TIMEOUT = 30


# =========================================================
# 5. Constants
# =========================================================

KOREA_REGIONS = (
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
)


ALLOWED_COMPANIONS = {
    "solo",
    "couple",
    "friend",
    "family",
}


ALLOWED_STYLES = {
    "healing",
    "nature",
    "food",
    "culture",
    "activity",
    "festival",
}


COMPANION_LABELS = {
    "solo": "혼자",
    "couple": "연인",
    "friend": "친구",
    "family": "가족",
}


STYLE_LABELS = {
    "healing": "힐링",
    "nature": "자연",
    "food": "맛집",
    "culture": "문화",
    "activity": "액티비티",
    "festival": "축제",
}


# =========================================================
# 6. Custom Exception
# =========================================================

class ServiceError(Exception):

    def __init__(
        self,
        code,
        message,
        status_code=500,
    ):
        super().__init__(message)

        self.code = code
        self.message = message
        self.status_code = status_code


# =========================================================
# 7. Environment Validation
# =========================================================

def get_api_keys():

    naito_api_key = os.getenv(
        "NAITO_API_KEY"
    )

    kakao_api_key = os.getenv(
        "KAKAO_API_KEY"
    )

    missing_keys = []

    if not naito_api_key:
        missing_keys.append(
            "NAITO_API_KEY"
        )

    if not kakao_api_key:
        missing_keys.append(
            "KAKAO_API_KEY"
        )

    if missing_keys:

        print(
            "[TripAI] Missing environment variables:",
            ", ".join(missing_keys),
        )

        raise ServiceError(
            code="SERVER_CONFIGURATION_ERROR",
            message=(
                "서비스 설정에 문제가 발생했습니다. "
                "잠시 후 다시 시도해주세요."
            ),
            status_code=500,
        )

    return (
        naito_api_key,
        kakao_api_key,
    )


# =========================================================
# 8. Request Validation
# =========================================================

def validate_date(value):

    if not isinstance(value, str):
        return None

    try:
        parsed_date = datetime.strptime(
            value,
            "%Y-%m-%d",
        )

        return parsed_date.strftime(
            "%Y-%m-%d"
        )

    except ValueError:
        return None


def validate_request(payload):

    if not isinstance(payload, dict):

        raise ServiceError(
            code="INVALID_REQUEST",
            message=(
                "입력한 여행 조건을 "
                "확인해주세요."
            ),
            status_code=400,
        )

    date = validate_date(
        payload.get("date")
    )

    if not date:

        raise ServiceError(
            code="INVALID_REQUEST",
            message=(
                "올바른 여행 날짜를 "
                "선택해주세요."
            ),
            status_code=400,
        )

    companion = payload.get(
        "companion"
    )

    if (
        companion is not None
        and companion not in ALLOWED_COMPANIONS
    ):

        raise ServiceError(
            code="INVALID_REQUEST",
            message=(
                "동행 선택 값을 "
                "확인해주세요."
            ),
            status_code=400,
        )

    styles = payload.get(
        "styles",
        [],
    )

    if not isinstance(styles, list):

        raise ServiceError(
            code="INVALID_REQUEST",
            message=(
                "여행 스타일 값을 "
                "확인해주세요."
            ),
            status_code=400,
        )

    for style in styles:

        if (
            not isinstance(style, str)
            or style not in ALLOWED_STYLES
        ):

            raise ServiceError(
                code="INVALID_REQUEST",
                message=(
                    "여행 스타일 값을 "
                    "확인해주세요."
                ),
                status_code=400,
            )

    # 중복 스타일 제거, 입력 순서는 유지
    styles = list(
        dict.fromkeys(styles)
    )

    return {
        "date": date,
        "companion": companion,
        "styles": styles,
    }


# =========================================================
# 9. Naito API
# =========================================================

def call_naito(
    api_key,
    messages,
):

    headers = {
        "Authorization": (
            f"Bearer {api_key}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }

    payload = {
        "model": NAITO_MODEL,
        "messages": messages,
    }

    try:

        response = requests.post(
            NAITO_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

        return (
            result["choices"][0]
            ["message"]["content"]
        )

    except requests.HTTPError as error:

        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        print(
            "[TripAI] Naito HTTP error:",
            status_code,
        )

        if status_code in (
            401,
            403,
        ):

            raise ServiceError(
                code="AI_AUTH_ERROR",
                message=(
                    "AI 서비스를 사용할 수 없습니다. "
                    "잠시 후 다시 시도해주세요."
                ),
                status_code=502,
            )

        if status_code == 429:

            raise ServiceError(
                code="RATE_LIMITED",
                message=(
                    "현재 요청이 많습니다. "
                    "잠시 후 다시 시도해주세요."
                ),
                status_code=429,
            )

        raise ServiceError(
            code="AI_API_ERROR",
            message=(
                "AI 서비스 요청 중 "
                "오류가 발생했습니다."
            ),
            status_code=502,
        )

    except requests.Timeout:

        print(
            "[TripAI] Naito timeout"
        )

        raise ServiceError(
            code="AI_TIMEOUT",
            message=(
                "AI 응답이 지연되고 있습니다. "
                "잠시 후 다시 시도해주세요."
            ),
            status_code=504,
        )

    except requests.RequestException as error:

        print(
            "[TripAI] Naito request error:",
            repr(error),
        )

        raise ServiceError(
            code="AI_API_ERROR",
            message=(
                "AI 서비스에 연결하지 "
                "못했습니다."
            ),
            status_code=502,
        )

    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as error:

        print(
            "[TripAI] Invalid Naito response:",
            repr(error),
        )

        raise ServiceError(
            code="INVALID_AI_RESPONSE",
            message=(
                "AI 응답을 처리하지 "
                "못했습니다."
            ),
            status_code=502,
        )


# =========================================================
# 10. User Preference Formatting
# =========================================================

def format_user_preferences(
    companion,
    styles,
):

    companion_text = (
        COMPANION_LABELS.get(
            companion,
            "지정하지 않음",
        )
    )

    if styles:

        style_text = ", ".join(
            STYLE_LABELS[style]
            for style in styles
        )

    else:

        style_text = "지정하지 않음"

    return (
        f"동행: {companion_text}\n"
        f"여행 스타일: {style_text}"
    )


# =========================================================
# 11. AI 1 - Travel Destination Recommendation
# =========================================================

def get_travel_recommendation(
    api_key,
    travel_request,
):

    preferences = (
        format_user_preferences(
            travel_request["companion"],
            travel_request["styles"],
        )
    )

    prompt = f"""
입력 여행 날짜:
{travel_request["date"]}

사용자 여행 조건:
{preferences}

해당 날짜와 여행 조건을 고려하여
대한민국 국내에서 여행하기 좋은 지역 1곳을 추천하세요.

반드시 아래 조건을 지켜주세요.

- 유효한 JSON 객체만 출력하세요.
- Markdown 코드블록을 사용하지 마세요.
- JSON 앞뒤에 설명을 작성하지 마세요.
- recommended_city는 대한민국 국내의 시/군/구 수준 지역이어야 합니다.
- recommended_city에는 광역자치단체명을 반드시 포함하세요.
- reason은 추천 근거를 2~4문장으로 작성하세요.
- seasonal_tip은 해당 여행 시기의 일반적인 여행 포인트나
  준비사항을 1~2문장으로 작성하세요.
- 여행 스타일에 축제가 포함된 경우, 여행 날짜의 계절성을 고려하여
  축제나 지역 행사를 즐기기 좋은 지역을 우선적으로 고려하세요.
- 현재 실시간 날씨라고 표현하지 마세요.
- 확인되지 않은 실제 행사나 축제를 만들어내지 마세요.
- 해외 지역을 추천하지 마세요.

출력 형식:

{{
  "recommended_city": "string",
  "reason": "string",
  "seasonal_tip": "string"
}}
"""

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    return call_naito(
        api_key,
        messages,
    )


def retry_travel_recommendation(
    api_key,
    travel_request,
):

    preferences = (
        format_user_preferences(
            travel_request["companion"],
            travel_request["styles"],
        )
    )

    prompt = f"""
입력 여행 날짜:
{travel_request["date"]}

사용자 여행 조건:
{preferences}

이전 응답은 JSON 파싱 또는 스키마 검증에 실패했습니다.

아래 세 개의 키만 포함한 유효한 JSON 객체를 출력하세요.

{{
  "recommended_city": "string",
  "reason": "string",
  "seasonal_tip": "string"
}}

조건:

- JSON 객체만 출력
- Markdown 코드블록 금지
- 추가 설명 금지
- recommended_city에는 대한민국 광역자치단체명과
  시/군/구를 포함
- reason은 2~4문장
- seasonal_tip은 1~2문장
- 해외 지역 금지
"""

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    return call_naito(
        api_key,
        messages,
    )


# =========================================================
# 12. Recommendation Validation
# =========================================================

def validate_recommendation(data):

    if not isinstance(data, dict):
        return False

    expected_keys = {
        "recommended_city",
        "reason",
        "seasonal_tip",
    }

    if set(data.keys()) != expected_keys:
        return False

    for key in expected_keys:

        if not isinstance(
            data.get(key),
            str,
        ):
            return False

        if not data[key].strip():
            return False

    city = data[
        "recommended_city"
    ].strip()

    if not city.startswith(
        KOREA_REGIONS
    ):
        return False

    return True


def parse_recommendation(text):

    try:

        data = json.loads(text)

    except json.JSONDecodeError:

        return None

    if not validate_recommendation(
        data
    ):

        return None

    return data


def create_recommendation(
    api_key,
    travel_request,
):

    first_response = (
        get_travel_recommendation(
            api_key,
            travel_request,
        )
    )

    recommendation = (
        parse_recommendation(
            first_response
        )
    )

    if recommendation is not None:

        return recommendation

    print(
        "[TripAI] Recommendation validation "
        "failed. Retrying once."
    )

    retry_response = (
        retry_travel_recommendation(
            api_key,
            travel_request,
        )
    )

    recommendation = (
        parse_recommendation(
            retry_response
        )
    )

    if recommendation is not None:

        return recommendation

    raise ServiceError(
        code="AI_GENERATION_FAILED",
        message=(
            "AI 여행지를 생성하지 못했습니다. "
            "잠시 후 다시 시도해주세요."
        ),
        status_code=502,
    )


# =========================================================
# 13. Kakao Local API
# =========================================================

def search_kakao_places(
    api_key,
    query,
    size=5,
):

    headers = {
        "Authorization": (
            f"KakaoAK {api_key}"
        )
    }

    params = {
        "query": query,
        "size": size,
    }

    response = requests.get(
        KAKAO_LOCAL_URL,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    result = response.json()

    documents = result.get(
        "documents",
        [],
    )

    places = []

    for place in documents:

        try:
            longitude = (
                float(place["x"])
                if place.get("x")
                else None
            )

            latitude = (
                float(place["y"])
                if place.get("y")
                else None
            )

        except (
            TypeError,
            ValueError,
        ):
            longitude = None
            latitude = None

        places.append(
            {
                "name": place.get(
                    "place_name",
                    "",
                ),
                "address": (
                    place.get(
                        "road_address_name"
                    )
                    or place.get(
                        "address_name",
                        "",
                    )
                ),
                "category": place.get(
                    "category_name",
                    "",
                ),
                "url": place.get(
                    "place_url",
                    "",
                ),
                "lng": longitude,
                "lat": latitude,
            }
        )

    return places


def safe_search_places(
    api_key,
    query,
    warning_code,
    warning_message,
):

    try:

        data = search_kakao_places(
            api_key,
            query,
        )

        return {
            "ok": True,
            "data": data,
            "warning": None,
        }

    except requests.HTTPError as error:

        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        print(
            "[TripAI] Kakao HTTP error:",
            status_code,
            query,
        )

    except requests.Timeout:

        print(
            "[TripAI] Kakao timeout:",
            query,
        )

    except (
        requests.RequestException,
        ValueError,
    ) as error:

        print(
            "[TripAI] Kakao request error:",
            query,
            repr(error),
        )

    return {
        "ok": False,
        "data": [],
        "warning": {
            "code": warning_code,
            "message": warning_message,
        },
    }


def collect_local_data(
    api_key,
    city,
):

    warnings = []

    # -------------------------
    # Tourist places
    # -------------------------

    place_result = (
        safe_search_places(
            api_key,
            f"{city} 관광명소",
            "PLACE_SEARCH_FAILED",
            (
                "일부 관광지 정보를 "
                "불러오지 못했습니다."
            ),
        )
    )

    places = place_result[
        "data"
    ]

    if place_result[
        "warning"
    ]:

        warnings.append(
            place_result[
                "warning"
            ]
        )

    # -------------------------
    # Restaurants
    # -------------------------

    restaurant_result = (
        safe_search_places(
            api_key,
            f"{city} 맛집",
            "RESTAURANT_SEARCH_FAILED",
            (
                "일부 맛집 정보를 "
                "불러오지 못했습니다."
            ),
        )
    )

    restaurants = (
        restaurant_result[
            "data"
        ]
    )

    if restaurant_result[
        "warning"
    ]:

        warnings.append(
            restaurant_result[
                "warning"
            ]
        )

    # API는 정상인데 검색 결과가 없는 경우
    if (
        place_result["ok"]
        and not places
    ):

        warnings.append(
            {
                "code": "PLACE_EMPTY",
                "message": (
                    "검색된 관광지 정보가 없습니다."
                ),
            }
        )

    if (
        restaurant_result["ok"]
        and not restaurants
    ):

        warnings.append(
            {
                "code": "RESTAURANT_EMPTY",
                "message": (
                    "검색된 맛집 정보가 없습니다."
                ),
            }
        )

    return (
        places,
        restaurants,
        warnings,
    )


# =========================================================
# 14. AI 2 - Final Itinerary
# =========================================================

def get_final_itinerary(
    api_key,
    travel_request,
    recommendation,
    places,
    restaurants,
):

    input_data = {
        "request": travel_request,
        "recommendation": recommendation,
        "places": places,
        "restaurants": restaurants,
    }

    prompt = f"""
다음 JSON 데이터를 바탕으로 국내 여행 일정을 작성하세요.

입력 데이터:

{json.dumps(
    input_data,
    ensure_ascii=False,
    indent=2,
)}

반드시 유효한 JSON 객체만 출력하세요.

출력 형식:

{{
  "title": "string",
  "morning": "string",
  "afternoon": "string",
  "evening": "string"
}}

작성 조건:

- Markdown 코드블록을 사용하지 마세요.
- JSON 앞뒤에 설명을 작성하지 마세요.
- title은 여행 컨셉을 한 문장으로 표현하세요.
- morning, afternoon, evening은 각각 1~3문장으로 작성하세요.
- 입력 데이터의 추천 지역을 벗어나지 마세요.
- places 또는 restaurants에 존재하지 않는 구체적인
  관광지나 음식점 이름을 새로 만들어내지 마세요.
- 장소 데이터가 부족하면 장소명을 억지로 추가하지 말고
  일반적인 여행 활동 수준으로 작성하세요.
- 비슷한 유형의 장소가 여러 개 포함되어 있어도 같은 유형을 반복해서 사용하지 말고,
  서로 다른 경험이 균형 있게 느껴지도록 일정을 구성하세요.
- 여행 스타일에 축제가 포함된 경우, 지역 문화 행사와 계절 행사 분위기를
  느낄 수 있는 여행 흐름으로 일정을 구성하세요.
- 사용자의 동행과 여행 스타일을 자연스럽게 반영하세요.
"""

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    return call_naito(
        api_key,
        messages,
    )


def retry_final_itinerary(
    api_key,
    travel_request,
    recommendation,
    places,
    restaurants,
):

    input_data = {
        "request": travel_request,
        "recommendation": recommendation,
        "places": places,
        "restaurants": restaurants,
    }

    prompt = f"""
이전 여행 일정 응답이 JSON 파싱 또는
스키마 검증에 실패했습니다.

다음 입력 데이터만 사용하세요.

{json.dumps(
    input_data,
    ensure_ascii=False,
    indent=2,
)}

아래 네 개의 키만 포함한 JSON 객체를 출력하세요.

{{
  "title": "string",
  "morning": "string",
  "afternoon": "string",
  "evening": "string"
}}

조건:

- 모든 값은 비어 있지 않은 문자열
- Markdown 금지
- 추가 설명 금지
"""

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    return call_naito(
        api_key,
        messages,
    )


# =========================================================
# 15. Itinerary Validation
# =========================================================

def validate_itinerary(data):

    if not isinstance(data, dict):
        return False

    expected_keys = {
        "title",
        "morning",
        "afternoon",
        "evening",
    }

    if set(data.keys()) != expected_keys:
        return False

    for key in expected_keys:

        if not isinstance(
            data.get(key),
            str,
        ):
            return False

        if not data[key].strip():
            return False

    return True


def parse_itinerary(text):

    try:

        data = json.loads(text)

    except json.JSONDecodeError:

        return None

    if not validate_itinerary(
        data
    ):

        return None

    return data


def create_final_itinerary(
    api_key,
    travel_request,
    recommendation,
    places,
    restaurants,
):

    first_response = (
        get_final_itinerary(
            api_key,
            travel_request,
            recommendation,
            places,
            restaurants,
        )
    )

    itinerary = (
        parse_itinerary(
            first_response
        )
    )

    if itinerary is not None:

        return itinerary

    print(
        "[TripAI] Itinerary validation "
        "failed. Retrying once."
    )

    retry_response = (
        retry_final_itinerary(
            api_key,
            travel_request,
            recommendation,
            places,
            restaurants,
        )
    )

    itinerary = (
        parse_itinerary(
            retry_response
        )
    )

    if itinerary is not None:

        return itinerary

    print(
        "[TripAI] Itinerary validation "
        "failed after retry."
    )

    return None


# =========================================================
# 16. Response Builder
# =========================================================

def build_success_response(
    recommendation,
    places,
    restaurants,
    itinerary,
    warnings,
):

    if itinerary is None:

        warnings.append(
            {
                "code": (
                    "ITINERARY_GENERATION_FAILED"
                ),
                "message": (
                    "세부 일정을 생성하지 "
                    "못했습니다."
                ),
            }
        )

        itinerary = {
            "title": (
                f"{recommendation['recommended_city']} 여행"
            ),
            "morning": (
                "추천 지역을 여유롭게 둘러보세요."
            ),
            "afternoon": (
                "추천 장소를 중심으로 "
                "여행을 이어가보세요."
            ),
            "evening": (
                "현지 맛집이나 주변 지역에서 "
                "여행을 마무리해보세요."
            ),
        }

    return {
        "ok": True,

        "recommendation": {
            "city": (
                recommendation[
                    "recommended_city"
                ]
            ),
            "reason": (
                recommendation[
                    "reason"
                ]
            ),
            "seasonal_tip": (
                recommendation[
                    "seasonal_tip"
                ]
            ),
            "title": (
                itinerary[
                    "title"
                ]
            ),
        },

        "places": places,

        "restaurants": restaurants,

        "itinerary": {
            "morning": (
                itinerary[
                    "morning"
                ]
            ),
            "afternoon": (
                itinerary[
                    "afternoon"
                ]
            ),
            "evening": (
                itinerary[
                    "evening"
                ]
            ),
        },

        "warnings": warnings,
    }


# =========================================================
# 17. Application Service
# =========================================================

def create_travel_plan(payload):

    # 1. 사용자 입력 검증
    travel_request = (
        validate_request(
            payload
        )
    )

    # 2. API Key 로드
    (
        naito_api_key,
        kakao_api_key,
    ) = get_api_keys()

    # 3. AI 여행지 추천
    recommendation = (
        create_recommendation(
            naito_api_key,
            travel_request,
        )
    )

    # 4. Kakao 관광지 / 맛집 검색
    (
        places,
        restaurants,
        warnings,
    ) = collect_local_data(
        kakao_api_key,
        recommendation[
            "recommended_city"
        ],
    )

    # 5. AI 최종 일정 생성
    itinerary = (
        create_final_itinerary(
            naito_api_key,
            travel_request,
            recommendation,
            places,
            restaurants,
        )
    )

    # 6. 최종 응답 구성
    return build_success_response(
        recommendation,
        places,
        restaurants,
        itinerary,
        warnings,
    )


# =========================================================
# 18. Frontend Route
# =========================================================

@app.get(
    "/",
    include_in_schema=False,
)
def home():

    index_file = (
        PROJECT_ROOT / "index.html"
    )

    if not index_file.exists():

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": (
                        "FRONTEND_NOT_FOUND"
                    ),
                    "message": (
                        "index.html을 찾을 수 없습니다."
                    ),
                },
            },
        )

    return FileResponse(
        path=str(index_file),
        media_type="text/html",
    )


# =========================================================
# 19. API Routes
# =========================================================

@app.post("/api/plan")
def plan(
    payload: dict = Body(...)
):

    try:

        print(
            "[TripAI] POST /api/plan"
        )

        result = (
            create_travel_plan(
                payload
            )
        )

        return JSONResponse(
            status_code=200,
            content=result,
        )

    except ServiceError as error:

        print(
            "[TripAI] ServiceError:",
            error.code,
            error.message,
        )

        return JSONResponse(
            status_code=error.status_code,
            content={
                "ok": False,
                "error": {
                    "code": (
                        error.code
                    ),
                    "message": (
                        error.message
                    ),
                },
            },
        )

    except Exception as error:

        # 상세 오류는 서버 로그에만 기록
        print(
            "[TripAI] Unexpected error:",
            repr(error),
        )

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": (
                        "INTERNAL_SERVER_ERROR"
                    ),
                    "message": (
                        "요청 처리 중 오류가 발생했습니다. "
                        "잠시 후 다시 시도해주세요."
                    ),
                },
            },
        )


@app.get("/api/plan")
def get_plan():

    return JSONResponse(
        status_code=405,
        content={
            "ok": False,
            "error": {
                "code": (
                    "METHOD_NOT_ALLOWED"
                ),
                "message": (
                    "POST 요청만 지원합니다."
                ),
            },
        },
    )


# =========================================================
# 20. Health Check
# =========================================================

@app.get(
    "/api/health",
    include_in_schema=False,
)
def health():

    return {
        "ok": True,
        "service": "TripAI",
    }