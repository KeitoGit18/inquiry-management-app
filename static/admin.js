const STATUS_OPEN = "未対応";
const STATUS_DONE = "対応済み";

const searchInput = document.getElementById("search-keyword");
const statusFilter = document.getElementById("status-filter");
const sortOrder = document.getElementById("sort-order");
const inquiryList = document.getElementById("inquiry-list");
const emptyMessage = document.getElementById("empty-message");
const inquiryCount = document.getElementById("inquiry-count");
const saveMessage = document.getElementById("save-message");

let inquiries = [];
const pendingInquiryIds = new Set();
let messageTimer;

searchInput.addEventListener("input", renderInquiries);
statusFilter.addEventListener("change", renderInquiries);
sortOrder.addEventListener("change", renderInquiries);

inquiryList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-id]");

  if (!button) {
    return;
  }

  const id = Number(button.dataset.id);

  if (!Number.isInteger(id) || pendingInquiryIds.has(id)) {
    return;
  }

  if (button.classList.contains("delete-button")) {
    const isConfirmed = window.confirm("本当に削除しますか？");

    if (isConfirmed) {
      await deleteInquiry(id);
    }

    return;
  }

  if (button.classList.contains("status-button")) {
    await toggleStatus(id);
  }
});

loadInquiries();

async function loadInquiries() {
  emptyMessage.textContent = "お問い合わせを読み込んでいます。";
  emptyMessage.style.display = "block";
  inquiryList.textContent = "";

  try {
    const savedInquiries = await requestJson(
      "/api/inquiries",
      {},
      "お問い合わせ一覧を取得できませんでした。サーバーが起動しているか確認してください。"
    );

    if (!Array.isArray(savedInquiries)) {
      throw new Error("お問い合わせ一覧の形式が正しくありません。");
    }

    inquiries = savedInquiries.map(normalizeInquiry);
    renderInquiries();
  } catch (error) {
    inquiries = [];
    renderInquiries();
    showMessage(
      getErrorMessage(error, "お問い合わせ一覧を取得できませんでした。"),
      true
    );
  }
}

function normalizeInquiry(inquiry) {
  return {
    id: inquiry.id,
    name: inquiry.name,
    email: inquiry.email,
    content: inquiry.content,
    status: inquiry.status,
    createdAt: inquiry.created_at
  };
}

function renderInquiries() {
  const filteredInquiries = getFilteredInquiries();
  const displayedInquiries = sortInquiriesByDate(filteredInquiries);

  inquiryList.textContent = "";
  inquiryCount.textContent = displayedInquiries.length + "件";
  emptyMessage.style.display = displayedInquiries.length === 0 ? "block" : "none";
  emptyMessage.textContent = hasActiveFilter()
    ? "該当するお問い合わせはありません"
    : "まだお問い合わせが登録されていません。";

  displayedInquiries.forEach((inquiry) => {
    const isDone = inquiry.status === STATUS_DONE;
    const isPending = pendingInquiryIds.has(inquiry.id);
    const listItem = document.createElement("li");
    listItem.className = "inquiry-card" + (isDone ? " is-done" : "");
    listItem.setAttribute("aria-busy", String(isPending));

    const topArea = document.createElement("div");
    topArea.className = "inquiry-top";

    const infoArea = document.createElement("div");

    const name = document.createElement("h3");
    name.className = "inquiry-name";
    name.textContent = inquiry.name;

    const email = document.createElement("span");
    email.className = "inquiry-email";
    email.textContent = inquiry.email;

    const date = document.createElement("span");
    date.className = "inquiry-date";
    date.textContent = "登録日時: " + formatCreatedAt(inquiry.createdAt);

    const statusBadge = document.createElement("span");
    statusBadge.className = "status-badge " + (isDone ? "is-done" : "is-open");
    statusBadge.textContent = inquiry.status;

    const actionArea = document.createElement("div");
    actionArea.className = "inquiry-actions";

    const statusButton = document.createElement("button");
    statusButton.className = "status-button" + (isDone ? " is-done" : "");
    statusButton.type = "button";
    statusButton.dataset.id = inquiry.id;
    statusButton.disabled = isPending;
    statusButton.setAttribute("aria-pressed", String(isDone));
    statusButton.textContent = isPending
      ? "更新中..."
      : isDone
        ? "未対応に戻す"
        : "対応済みにする";

    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.type = "button";
    deleteButton.dataset.id = inquiry.id;
    deleteButton.disabled = isPending;
    deleteButton.textContent = "削除";

    const content = document.createElement("p");
    content.className = "inquiry-body";
    content.textContent = inquiry.content;

    infoArea.append(name, email, date, statusBadge);
    actionArea.append(statusButton, deleteButton);
    topArea.append(infoArea, actionArea);
    listItem.append(topArea, content);
    inquiryList.appendChild(listItem);
  });
}

function getFilteredInquiries() {
  const keyword = searchInput.value.trim().toLowerCase();
  const selectedStatus = statusFilter.value;

  return inquiries.filter((inquiry) => {
    const searchableText = (inquiry.name + " " + inquiry.email + " " + inquiry.content)
      .toLowerCase();
    const matchesKeyword = !keyword || searchableText.includes(keyword);
    const matchesStatus = selectedStatus === "all" || inquiry.status === selectedStatus;

    return matchesKeyword && matchesStatus;
  });
}

function sortInquiriesByDate(inquiriesToSort) {
  return [...inquiriesToSort].sort((first, second) => {
    const firstTimestamp = getCreatedTimestamp(first.createdAt);
    const secondTimestamp = getCreatedTimestamp(second.createdAt);

    if (firstTimestamp === null && secondTimestamp === null) {
      return 0;
    }

    if (firstTimestamp === null) {
      return 1;
    }

    if (secondTimestamp === null) {
      return -1;
    }

    return sortOrder.value === "oldest"
      ? firstTimestamp - secondTimestamp
      : secondTimestamp - firstTimestamp;
  });
}

function getCreatedTimestamp(createdAt) {
  if (!createdAt) {
    return null;
  }

  const date = new Date(createdAt);
  const timestamp = date.getTime();

  return Number.isNaN(timestamp) ? null : timestamp;
}

function formatCreatedAt(createdAt) {
  const timestamp = getCreatedTimestamp(createdAt);

  if (timestamp === null) {
    return "日時不明";
  }

  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");

  return year + "/" + month + "/" + day + " " + hours + ":" + minutes;
}

function hasActiveFilter() {
  return searchInput.value.trim() !== "" || statusFilter.value !== "all";
}

async function toggleStatus(id) {
  const inquiry = inquiries.find((item) => item.id === id);

  if (!inquiry) {
    return;
  }

  const nextStatus = inquiry.status === STATUS_DONE ? STATUS_OPEN : STATUS_DONE;
  pendingInquiryIds.add(id);
  renderInquiries();

  try {
    const updatedInquiry = await requestJson(
      "/api/inquiries/" + id + "/status",
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus })
      },
      "対応状況を更新できませんでした。通信状況を確認して、もう一度お試しください。"
    );

    if (!updatedInquiry || typeof updatedInquiry.status !== "string") {
      throw new Error("対応状況の更新結果を確認できませんでした。");
    }

    inquiries = inquiries.map((item) => {
      if (item.id !== id) {
        return item;
      }

      return { ...item, status: updatedInquiry.status };
    });
    showMessage("対応状況を更新しました。");
  } catch (error) {
    showMessage(getErrorMessage(error, "対応状況を更新できませんでした。"), true);
  } finally {
    pendingInquiryIds.delete(id);
    renderInquiries();
  }
}

async function deleteInquiry(id) {
  pendingInquiryIds.add(id);
  renderInquiries();

  try {
    await requestJson(
      "/api/inquiries/" + id,
      { method: "DELETE" },
      "お問い合わせを削除できませんでした。通信状況を確認して、もう一度お試しください。"
    );

    inquiries = inquiries.filter((inquiry) => inquiry.id !== id);
    showMessage("お問い合わせを削除しました。");
  } catch (error) {
    showMessage(getErrorMessage(error, "お問い合わせを削除できませんでした。"), true);
  } finally {
    pendingInquiryIds.delete(id);
    renderInquiries();
  }
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
