import json
import os
from datetime import datetime

import requests

from dotenv import load_dotenv
from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse


# =========================================================
# 1. Environment
# =========================================================

load_dotenv()

app = FastAPI(
    title="TripAI API"
)


# =========================================================
# 2. External API Configuration
# =========================================================

NAITO_URL = "https://copa.codyssey.kr/v1/chat/completions"
NAITO_MODEL = "gpt-5.5"

KAKAO_LOCAL_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)

REQUEST_TIMEOUT = 30


# =========================================================
# 3. Constants
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
}


# =========================================================
# 4. Custom Exceptions
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
# 5. Environment Validation
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
# 6. Request Validation
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

    if companion is not None:
        if companion not in ALLOWED_COMPANIONS:
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

    if not all(
        isinstance(style, str)
        and style in ALLOWED_STYLES
        for style in styles
    ):
        raise ServiceError(
            code="INVALID_REQUEST",
            message=(
                "여행 스타일 값을 "
                "확인해주세요."
            ),
            status_code=400,
        )

    # 같은 스타일이 중복 전달되더라도
    # 최초 순서를 유지하며 제거
    styles = list(
        dict.fromkeys(styles)
    )

    return {
        "date": date,
        "companion": companion,
        "styles": styles,
    }


# =========================================================
# 7. Naito API
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

    data = {
        "model": NAITO_MODEL,
        "messages": messages,
    }

    try:
        response = requests.post(
            NAITO_URL,
            headers=headers,
            json=data,
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
            "[TripAI] Naito API timeout"
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
            error,
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
        ValueError,
    ) as error:
        print(
            "[TripAI] Invalid Naito response:",
            error,
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
# 8. Recommendation Prompt
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

    style_text = (
        ", ".join(
            STYLE_LABELS[style]
            for style in styles
        )
        if styles
        else "지정하지 않음"
    )

    return (
        f"동행: {companion_text}\n"
        f"여행 스타일: {style_text}"
    )


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

    messages = [
        {
            "role": "user",
            "content": f"""
입력 여행 날짜:
{travel_request["date"]}

사용자 여행 조건:
{preferences}

해당 날짜와 여행 조건을 고려하여
대한민국 국내에서 여행하기 좋은
지역 1곳을 추천하세요.

반드시 아래 조건을 지켜주세요.

- 유효한 JSON 객체만 출력하세요.
- Markdown 코드블록을 사용하지 마세요.
- JSON 앞뒤에 설명을 작성하지 마세요.
- recommended_city는 대한민국 국내의
  시/군/구 수준 지역이어야 합니다.
- 광역자치단체명을 반드시 포함하세요.
- reason은 추천 근거를 2~4문장으로
  작성하세요.
- seasonal_tip은 해당 여행 시기의
  일반적인 여행 포인트나 준비사항을
  1~2문장으로 작성하세요.
- 현재 실시간 날씨라고 표현하지 마세요.
- 확인되지 않은 실제 행사나 축제를
  만들어내지 마세요.
- 해외 지역을 추천하지 마세요.

출력 형식:

{{
  "recommended_city": "string",
  "reason": "string",
  "seasonal_tip": "string"
}}
"""
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

    messages = [
        {
            "role": "user",
            "content": f"""
입력 여행 날짜:
{travel_request["date"]}

사용자 여행 조건:
{preferences}

이전 응답은 JSON 파싱 또는
스키마 검증에 실패했습니다.

아래 3개 키만 포함한
유효한 JSON 객체를 출력하세요.

- recommended_city: string
- reason: string
- seasonal_tip: string

추가 조건:

- JSON 객체만 출력하세요.
- Markdown 코드블록 금지
- 설명 문장 추가 금지
- recommended_city에는 대한민국
  광역자치단체명과 시/군/구를
  포함하세요.
- reason은 2~4문장
- seasonal_tip은 1~2문장
- 해외 지역 금지

출력 형식:

{{
  "recommended_city": "string",
  "reason": "string",
  "seasonal_tip": "string"
}}
"""
        }
    ]

    return call_naito(
        api_key,
        messages,
    )


# =========================================================
# 9. Recommendation Validation
# =========================================================

def validate_recommendation(data):
    if not isinstance(data, dict):
        return False

    required_fields = {
        "recommended_city": str,
        "reason": str,
        "seasonal_tip": str,
    }

    if set(data.keys()) != set(
        required_fields.keys()
    ):
        return False

    for key, expected_type in (
        required_fields.items()
    ):
        if not isinstance(
            data[key],
            expected_type,
        ):
            return False

        if not data[key].strip():
            return False

    if not data[
        "recommended_city"
    ].startswith(KOREA_REGIONS):
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
        "[TripAI] Recommendation "
        "schema validation failed. "
        "Retrying once."
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

    print(
        "[TripAI] Recommendation "
        "validation failed after retry."
    )

    raise ServiceError(
        code="AI_GENERATION_FAILED",
        message=(
            "AI 여행지를 생성하지 못했습니다. "
            "잠시 후 다시 시도해주세요."
        ),
        status_code=502,
    )


# =========================================================
# 10. Kakao Local API
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
        return search_kakao_places(
            api_key,
            query,
        )

    except requests.HTTPError as error:
        status_code = (
            error.response.status_code
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
            error,
        )

    return {
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

    place_result = safe_search_places(
        api_key,
        f"{city} 관광명소",
        "PLACE_SEARCH_FAILED",
        (
            "일부 관광지 정보를 "
            "불러오지 못했습니다."
        ),
    )

    if isinstance(
        place_result,
        dict,
    ):
        places = place_result["data"]
        warnings.append(
            place_result["warning"]
        )
    else:
        places = place_result

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

    if isinstance(
        restaurant_result,
        dict,
    ):
        restaurants = (
            restaurant_result["data"]
        )

        warnings.append(
            restaurant_result["warning"]
        )

    else:
        restaurants = (
            restaurant_result
        )

    if not places:
        warnings.append(
            {
                "code": "PLACE_EMPTY",
                "message": (
                    "검색된 관광지 정보가 "
                    "없습니다."
                ),
            }
        )

    if not restaurants:
        warnings.append(
            {
                "code": (
                    "RESTAURANT_EMPTY"
                ),
                "message": (
                    "검색된 맛집 정보가 "
                    "없습니다."
                ),
            }
        )

    return (
        places,
        restaurants,
        warnings,
    )


# =========================================================
# 11. Final Itinerary Prompt
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
        "recommendation": (
            recommendation
        ),
        "places": places,
        "restaurants": restaurants,
    }

    messages = [
        {
            "role": "user",
            "content": f"""
다음 JSON 데이터를 바탕으로
국내 여행 일정을 작성하세요.

입력 데이터:

{json.dumps(
    input_data,
    ensure_ascii=False,
    indent=2,
)}

반드시 유효한 JSON 객체만
출력하세요.

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
- title은 여행 컨셉을 한 문장으로
  표현하세요.
- morning, afternoon, evening은
  각각 1~3문장으로 작성하세요.
- 입력 데이터의 추천 지역을
  벗어나지 마세요.
- places 또는 restaurants에 존재하지 않는
  구체적인 관광지나 음식점 이름을
  새로 만들어내지 마세요.
- 장소 데이터가 부족하면 장소명을
  억지로 추가하지 말고 일반적인
  여행 활동 수준으로 작성하세요.
- 사용자의 동행과 여행 스타일을
  자연스럽게 반영하세요.
"""
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
        "recommendation": (
            recommendation
        ),
        "places": places,
        "restaurants": restaurants,
    }

    messages = [
        {
            "role": "user",
            "content": f"""
이전 여행 일정 응답이
JSON 파싱 또는 스키마 검증에
실패했습니다.

다음 입력 데이터만 사용하세요.

{json.dumps(
    input_data,
    ensure_ascii=False,
    indent=2,
)}

아래 4개 키만 포함한
JSON 객체를 출력하세요.

{{
  "title": "string",
  "morning": "string",
  "afternoon": "string",
  "evening": "string"
}}

모든 값은 비어 있지 않은
문자열이어야 합니다.

Markdown과 추가 설명은
사용하지 마세요.
"""
        }
    ]

    return call_naito(
        api_key,
        messages,
    )


# =========================================================
# 12. Final Itinerary Validation
# =========================================================

def validate_itinerary(data):
    if not isinstance(data, dict):
        return False

    required_fields = {
        "title": str,
        "morning": str,
        "afternoon": str,
        "evening": str,
    }

    if set(data.keys()) != set(
        required_fields.keys()
    ):
        return False

    for key, expected_type in (
        required_fields.items()
    ):
        if not isinstance(
            data[key],
            expected_type,
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

    if not validate_itinerary(data):
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

    itinerary = parse_itinerary(
        first_response
    )

    if itinerary is not None:
        return itinerary

    print(
        "[TripAI] Itinerary schema "
        "validation failed. "
        "Retrying once."
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

    itinerary = parse_itinerary(
        retry_response
    )

    if itinerary is not None:
        return itinerary

    print(
        "[TripAI] Itinerary validation "
        "failed after retry."
    )

    return None


# =========================================================
# 13. Response Builder
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
                f"{recommendation['recommended_city']} "
                "여행"
            ),
            "morning": (
                "추천 지역을 여유롭게 "
                "둘러보세요."
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
            "city": recommendation[
                "recommended_city"
            ],
            "reason": recommendation[
                "reason"
            ],
            "seasonal_tip": (
                recommendation[
                    "seasonal_tip"
                ]
            ),
            "title": itinerary[
                "title"
            ],
        },

        "places": places,

        "restaurants": restaurants,

        "itinerary": {
            "morning": itinerary[
                "morning"
            ],
            "afternoon": itinerary[
                "afternoon"
            ],
            "evening": itinerary[
                "evening"
            ],
        },

        "warnings": warnings,
    }


# =========================================================
# 14. Application Service
# =========================================================

def create_travel_plan(payload):
    travel_request = (
        validate_request(payload)
    )

    (
        naito_api_key,
        kakao_api_key,
    ) = get_api_keys()

    recommendation = (
        create_recommendation(
            naito_api_key,
            travel_request,
        )
    )

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

    itinerary = (
        create_final_itinerary(
            naito_api_key,
            travel_request,
            recommendation,
            places,
            restaurants,
        )
    )

    return build_success_response(
        recommendation,
        places,
        restaurants,
        itinerary,
        warnings,
    )

# =========================================================
# FastAPI Routes
# =========================================================

@app.post("/api/plan")
def plan(payload: dict = Body(...)):
    try:
        result = create_travel_plan(payload)

        return JSONResponse(
            status_code=200,
            content=result,
        )

    except ServiceError as error:
        print(
            "[TripAI] ServiceError:",
            error.code,
            error,
        )

        return JSONResponse(
            status_code=error.status_code,
            content={
                "ok": False,
                "error": {
                    "code": error.code,
                    "message": error.message,
                },
            },
        )

    except Exception as error:
        print(
            "[TripAI] Unexpected error:",
            repr(error),
        )

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
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
                "code": "METHOD_NOT_ALLOWED",
                "message": "POST 요청만 지원합니다.",
            },
        },
    )