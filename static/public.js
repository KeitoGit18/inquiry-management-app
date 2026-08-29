const form = document.getElementById("inquiry-form");
const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const contentInput = document.getElementById("content");
const saveMessage = document.getElementById("save-message");
const formControls = form.querySelectorAll("input, textarea, button");
const submitButton = form.querySelector('button[type="submit"]');

let isSubmitting = false;
let messageTimer;

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (isSubmitting) {
    return;
  }

  const inquiry = {
    name: nameInput.value.trim(),
    email: emailInput.value.trim(),
    content: contentInput.value.trim()
  };

  if (!inquiry.name || !inquiry.email || !inquiry.content) {
    showMessage("すべての項目を入力してください。", true);
    return;
  }

  isSubmitting = true;
  updateFormState();

  try {
    const savedInquiry = await requestJson(
      "/api/inquiries",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(inquiry)
      },
      "お問い合わせを送信できませんでした。通信状況を確認して、もう一度お試しください。"
    );

    if (!savedInquiry || typeof savedInquiry !== "object") {
      throw new Error("お問い合わせの送信結果を確認できませんでした。");
    }

    form.reset();
    showMessage("お問い合わせを送信しました。ありがとうございます。");
    nameInput.focus();
  } catch (error) {
    showMessage(
      getErrorMessage(error, "お問い合わせを送信できませんでした。"),
      true
    );
  } finally {
    isSubmitting = false;
    updateFormState();
  }
});

function updateFormState() {
  formControls.forEach((control) => {
    control.disabled = isSubmitting;
  });

  submitButton.textContent = isSubmitting ? "送信中..." : "送信する";
}

async function requestJson(url, options, fallbackMessage) {
  let response;

  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(fallbackMessage);
  }

  const data = await readResponseJson(response);

  if (!response.ok) {
    throw new Error(getApiErrorMessage(data, fallbackMessage));
  }

  return data;
}

async function readResponseJson(response) {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

function getApiErrorMessage(data, fallbackMessage) {
  return data && typeof data.error === "string" ? data.error : fallbackMessage;
}

function getErrorMessage(error, fallbackMessage) {
  return error instanceof Error && error.message ? error.message : fallbackMessage;
}

function showMessage(message, isError = false) {
  clearTimeout(messageTimer);
  saveMessage.textContent = message;
  saveMessage.classList.toggle("error", isError);
  saveMessage.setAttribute("role", isError ? "alert" : "status");
  saveMessage.classList.add("show");

  messageTimer = setTimeout(() => {
    saveMessage.classList.remove("show");
  }, isError ? 5000 : 3000);
}
