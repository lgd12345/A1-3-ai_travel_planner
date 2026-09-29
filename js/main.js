/* =========================================================
   TripAI - Main
   Navigation / Form / API / Result Rendering
   ========================================================= */


/* =========================================================
   1. Constants
   ========================================================= */

const API_ENDPOINT = "/api/plan";
const REQUEST_TIMEOUT_MS = 60000;

const LOADING_MESSAGES = [
  "여행 조건을 확인하고 있습니다...",
  "AI가 어울리는 여행지를 분석하고 있습니다...",
  "추천 지역의 실제 장소를 찾고 있습니다...",
  "여행 일정을 구성하고 있습니다..."
];


/* =========================================================
   2. DOM Elements
   ========================================================= */

const menuToggleButton =
  document.getElementById("menuToggle");

const mobileNav =
  document.getElementById("mobileNav");

const plannerForm =
  document.getElementById("plannerForm");

const travelDateInput =
  document.getElementById("travelDate");

const dateError =
  document.getElementById("dateError");

const generateButton =
  document.getElementById("generateButton");

const loadingState =
  document.getElementById("loadingState");

const loadingMessage =
  document.getElementById("loadingMessage");

const resultSection =
  document.getElementById("resultSection");

const globalError =
  document.getElementById("globalError");


/* =========================================================
   3. Mobile Navigation
   ========================================================= */

function openMobileMenu() {
  if (!mobileNav || !menuToggleButton) {
    return;
  }

  mobileNav.hidden = false;

  menuToggleButton.setAttribute(
    "aria-expanded",
    "true"
  );

  menuToggleButton.setAttribute(
    "aria-label",
    "모바일 메뉴 닫기"
  );
}


function closeMobileMenu() {
  if (!mobileNav || !menuToggleButton) {
    return;
  }

  mobileNav.hidden = true;

  menuToggleButton.setAttribute(
    "aria-expanded",
    "false"
  );

  menuToggleButton.setAttribute(
    "aria-label",
    "모바일 메뉴 열기"
  );
}


function toggleMobileMenu() {
  if (!mobileNav) {
    return;
  }

  if (mobileNav.hidden) {
    openMobileMenu();
    return;
  }

  closeMobileMenu();
}


function initializeMobileNavigation() {
  if (!menuToggleButton || !mobileNav) {
    return;
  }

  menuToggleButton.addEventListener(
    "click",
    toggleMobileMenu
  );

  mobileNav
    .querySelectorAll("a")
    .forEach((link) => {
      link.addEventListener(
        "click",
        closeMobileMenu
      );
    });

  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape" &&
        !mobileNav.hidden
      ) {
        closeMobileMenu();

        menuToggleButton.focus();
      }
    }
  );

  window.addEventListener(
    "resize",
    () => {
      if (window.innerWidth >= 1024) {
        closeMobileMenu();
      }
    }
  );
}


/* =========================================================
   4. Form Data
   ========================================================= */

function getSelectedCompanion() {
  const selected =
    plannerForm?.querySelector(
      'input[name="companion"]:checked'
    );

  return selected
    ? selected.value
    : null;
}

function initializeCompanionSelection() {
  if (!plannerForm) {
    return;
  }

  const companionInputs =
    plannerForm.querySelectorAll(
      'input[name="companion"]'
    );

  companionInputs.forEach(
    (input) => {
      input.addEventListener(
        "change",
        () => {
          if (!input.checked) {
            return;
          }

          companionInputs.forEach(
            (otherInput) => {
              if (
                otherInput !== input
              ) {
                otherInput.checked = false;
              }
            }
          );
        }
      );
    }
  );
}


function getSelectedStyles() {
  if (!plannerForm) {
    return [];
  }

  return Array.from(
    plannerForm.querySelectorAll(
      'input[name="styles"]:checked'
    )
  ).map((input) => input.value);
}


function getFormData() {
  return {
    date: travelDateInput.value,
    companion: getSelectedCompanion(),
    styles: getSelectedStyles()
  };
}


/* =========================================================
   5. Validation
   ========================================================= */

function formatLocalDate(date) {
  const year = date.getFullYear();

  const month = String(
    date.getMonth() + 1
  ).padStart(2, "0");

  const day = String(
    date.getDate()
  ).padStart(2, "0");

  return `${year}-${month}-${day}`;
}


function setTravelDateRange() {
  if (!travelDateInput) {
    return;
  }

  const today = new Date();

  const maxDate = new Date(today);

  maxDate.setFullYear(
    today.getFullYear() + 1
  );

  travelDateInput.min =
    formatLocalDate(today);

  travelDateInput.max =
    formatLocalDate(maxDate);
}


function clearValidationErrors() {
  if (dateError) {
    dateError.textContent = "";
  }

  if (travelDateInput) {
    travelDateInput.removeAttribute(
      "aria-invalid"
    );
  }
}


function validateForm() {
  clearValidationErrors();

  if (!travelDateInput.value) {
    dateError.textContent =
      "여행 날짜를 선택해주세요.";

    travelDateInput.setAttribute(
      "aria-invalid",
      "true"
    );

    travelDateInput.focus();

    return false;
  }

  if (
    travelDateInput.value <
    travelDateInput.min ||
    travelDateInput.value >
    travelDateInput.max
  ) {
    dateError.textContent =
      "여행 날짜는 오늘부터 1년 이내로 선택해주세요.";

    travelDateInput.setAttribute(
      "aria-invalid",
      "true"
    );

    travelDateInput.focus();

    return false;
  }

  return true;
}


/* =========================================================
   6. UI State
   ========================================================= */

function clearGlobalError() {
  globalError.hidden = true;
  globalError.textContent = "";
}


function showGlobalError(message) {
  globalError.textContent = message;
  globalError.hidden = false;

  globalError.scrollIntoView({
    behavior: "smooth",
    block: "nearest"
  });
}


function clearResult() {
  resultSection.replaceChildren();
  resultSection.hidden = true;
}


function setSubmitting(isSubmitting) {
  generateButton.disabled = isSubmitting;

  generateButton.textContent = isSubmitting
    ? "여행 플랜 생성 중..."
    : "AI 여행 플랜 만들기";
}


/* =========================================================
   7. Loading State
   ========================================================= */

let loadingTimerIds = [];


function clearLoadingTimers() {
  loadingTimerIds.forEach(
    (timerId) => clearTimeout(timerId)
  );

  loadingTimerIds = [];
}


function startLoading() {
  clearLoadingTimers();

  loadingMessage.textContent =
    LOADING_MESSAGES[0];

  loadingState.hidden = false;

  /*
   * 실제 서버 진행률을 전달받는 구조는 아니므로
   * 사용자에게 대기 상태를 안내하기 위한 UX 메시지이다.
   */

  const delays = [
    1800,
    4500,
    8000
  ];

  delays.forEach(
    (delay, index) => {
      const timerId = setTimeout(
        () => {
          loadingMessage.textContent =
            LOADING_MESSAGES[index + 1];
        },
        delay
      );

      loadingTimerIds.push(timerId);
    }
  );
}


function stopLoading() {
  clearLoadingTimers();

  loadingState.hidden = true;
}


/* =========================================================
   8. API Request
   ========================================================= */

async function requestTravelPlan(payload) {
  const controller =
    new AbortController();

  const timeoutId = setTimeout(
    () => {
      controller.abort();
    },
    REQUEST_TIMEOUT_MS
  );

  try {
    const response = await fetch(
      API_ENDPOINT,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify(payload),

        signal: controller.signal
      }
    );

    let data;

    try {
      data = await response.json();
    } catch {
      throw new Error(
        "INVALID_SERVER_RESPONSE"
      );
    }

    if (!response.ok) {
      const error = new Error(
        data?.error?.message ||
        "요청 처리 중 오류가 발생했습니다."
      );

      error.code =
        data?.error?.code ||
        `HTTP_${response.status}`;

      throw error;
    }

    if (!data || data.ok !== true) {
      throw new Error(
        "INVALID_SERVER_RESPONSE"
      );
    }

    return data;

  } finally {
    clearTimeout(timeoutId);
  }
}


/* =========================================================
   9. DOM Helpers
   ========================================================= */

function createElement(
  tagName,
  className,
  text
) {
  const element =
    document.createElement(tagName);

  if (className) {
    element.className = className;
  }

  if (
    text !== undefined &&
    text !== null
  ) {
    element.textContent = text;
  }

  return element;
}


function createSectionTitle(title) {
  return createElement(
    "h3",
    "result-section-title",
    title
  );
}


/* =========================================================
   10. Recommendation
   ========================================================= */

function createRecommendationBlock(
  recommendation
) {
  const article =
    createElement(
      "article",
      "result-hero"
    );

  const eyebrow =
    createElement(
      "p",
      "eyebrow",
      "AI PICK"
    );

  const city =
    createElement(
      "h2",
      "result-city",
      recommendation?.city ||
      "추천 여행지"
    );

  const reason =
    createElement(
      "p",
      "result-reason",
      recommendation?.reason ||
      "추천 정보를 불러오지 못했습니다."
    );

  article.append(
    eyebrow,
    city,
    reason
  );

  if (recommendation?.seasonal_tip) {
    const tip =
      createElement(
        "div",
        "result-tip"
      );

    const tipTitle =
      createElement(
        "strong",
        "",
        "여행 시기 포인트"
      );

    const tipText =
      createElement(
        "p",
        "",
        recommendation.seasonal_tip
      );

    tip.append(
      tipTitle,
      tipText
    );

    article.append(tip);
  }

  return article;
}


/* =========================================================
   11. Place Cards
   ========================================================= */

function createPlaceCard(place) {
  const article =
    createElement(
      "article",
      "result-card place-card"
    );

  const name =
    createElement(
      "h3",
      "",
      place?.name ||
      "장소 정보"
    );

  article.append(name);

  if (place?.category) {
    const category =
      createElement(
        "p",
        "place-category",
        place.category
      );

    article.append(category);
  }

  if (place?.address) {
    const address =
      createElement(
        "p",
        "place-address",
        place.address
      );

    article.append(address);
  }

  if (place?.url) {
    const link =
      createElement(
        "a",
        "place-link",
        "장소 정보 보기"
      );

    link.href = place.url;

    link.target = "_blank";
    link.rel = "noopener noreferrer";

    article.append(link);
  }

  return article;
}


function createPlacesBlock(
  title,
  places
) {
  const section =
    createElement(
      "section",
      "result-block"
    );

  section.append(
    createSectionTitle(title)
  );

  if (
    !Array.isArray(places) ||
    places.length === 0
  ) {
    const emptyMessage =
      createElement(
        "p",
        "result-empty",
        "검색된 정보가 없습니다."
      );

    section.append(emptyMessage);

    return section;
  }

  const grid =
    createElement(
      "div",
      "result-grid"
    );

  places.forEach(
    (place) => {
      grid.append(
        createPlaceCard(place)
      );
    }
  );

  section.append(grid);

  return section;
}


/* =========================================================
   12. Itinerary
   ========================================================= */

function createItineraryItem(
  label,
  value
) {
  const article =
    createElement(
      "article",
      "result-card itinerary-card"
    );

  const labelElement =
    createElement(
      "span",
      "itinerary-label",
      label
    );

  const description =
    createElement(
      "p",
      "",
      value ||
      "일정 정보가 없습니다."
    );

  article.append(
    labelElement,
    description
  );

  return article;
}


function createItineraryBlock(
  itinerary
) {
  const section =
    createElement(
      "section",
      "result-block"
    );

  section.append(
    createSectionTitle("YOUR DAY")
  );

  const grid =
    createElement(
      "div",
      "result-grid itinerary-grid"
    );

  grid.append(
    createItineraryItem(
      "MORNING",
      itinerary?.morning
    ),

    createItineraryItem(
      "AFTERNOON",
      itinerary?.afternoon
    ),

    createItineraryItem(
      "EVENING",
      itinerary?.evening
    )
  );

  section.append(grid);

  return section;
}


/* =========================================================
   13. Warnings
   ========================================================= */

function createWarningsBlock(
  warnings
) {
  if (
    !Array.isArray(warnings) ||
    warnings.length === 0
  ) {
    return null;
  }

  const aside =
    createElement(
      "aside",
      "result-warning"
    );

  const title =
    createElement(
      "strong",
      "",
      "일부 정보를 불러오지 못했습니다."
    );

  const list =
    createElement("ul");

  warnings.forEach(
    (warning) => {
      const message =
        typeof warning === "string"
          ? warning
          : warning?.message;

      if (!message) {
        return;
      }

      list.append(
        createElement(
          "li",
          "",
          message
        )
      );
    }
  );

  aside.append(
    title,
    list
  );

  return aside;
}


/* =========================================================
   14. Result Rendering
   ========================================================= */

function renderResult(data) {
  resultSection.replaceChildren();

  const fragment =
    document.createDocumentFragment();

  fragment.append(
    createRecommendationBlock(
      data.recommendation
    )
  );

  fragment.append(
    createPlacesBlock(
      "추천 장소",
      data.places
    )
  );

  fragment.append(
    createPlacesBlock(
      "맛집",
      data.restaurants
    )
  );

  fragment.append(
    createItineraryBlock(
      data.itinerary
    )
  );

  const warnings =
    createWarningsBlock(
      data.warnings
    );

  if (warnings) {
    fragment.append(warnings);
  }

  resultSection.append(fragment);

  resultSection.hidden = false;

  resultSection.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}


/* =========================================================
   15. Error Translation
   ========================================================= */

function getUserErrorMessage(error) {
  if (error.name === "AbortError") {
    return (
      "응답 시간이 너무 오래 걸리고 있습니다. " +
      "잠시 후 다시 시도해주세요."
    );
  }

  switch (error.code) {
    case "RATE_LIMITED":
    case "QUOTA_ERROR":
    case "HTTP_429":
      return (
        "현재 요청이 많습니다. " +
        "잠시 후 다시 시도해주세요."
      );

    case "INVALID_REQUEST":
      return (
        "입력한 여행 조건을 확인해주세요."
      );

    case "AI_GENERATION_FAILED":
      return (
        "AI 여행 계획을 생성하지 못했습니다. " +
        "잠시 후 다시 시도해주세요."
      );

    case "INVALID_SERVER_RESPONSE":
      return (
        "서버 응답을 처리하지 못했습니다. " +
        "잠시 후 다시 시도해주세요."
      );

    default:
      return (
        error.message &&
        error.message !==
        "INVALID_SERVER_RESPONSE"
      )
        ? error.message
        : (
          "요청 처리 중 오류가 발생했습니다. " +
          "잠시 후 다시 시도해주세요."
        );
  }
}


/* =========================================================
   16. Form Submit
   ========================================================= */

async function handlePlannerSubmit(event) {
  event.preventDefault();

  clearGlobalError();

  if (!validateForm()) {
    return;
  }

  const payload =
    getFormData();

  clearResult();

  setSubmitting(true);
  startLoading();

  try {
    const result =
      await requestTravelPlan(payload);

    renderResult(result);

  } catch (error) {
    console.error(
      "[TripAI] Travel plan request failed:",
      error
    );

    showGlobalError(
      getUserErrorMessage(error)
    );

  } finally {
    stopLoading();
    setSubmitting(false);
  }
}


/* =========================================================
   17. Initialize
   ========================================================= */

function initializeApp() {
  initializeMobileNavigation();
  setTravelDateRange();
  initializeCompanionSelection();

  if (plannerForm) {
    plannerForm.addEventListener(
      "submit",
      handlePlannerSubmit
    );
  }

  if (travelDateInput) {
    travelDateInput.addEventListener(
      "input",
      () => {
        if (travelDateInput.value) {
          clearValidationErrors();
        }
      }
    );
  }
}


initializeApp();