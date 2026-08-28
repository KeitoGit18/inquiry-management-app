const STORAGE_KEY = "beginnerInquiryList";
const STATUS_OPEN = "未対応";
const STATUS_DONE = "対応済み";

const form = document.getElementById("inquiry-form");
const nameInput = document.getElementById("name");
const emailInput = document.getElementById("email");
const contentInput = document.getElementById("content");
const searchInput = document.getElementById("search-keyword");
const statusFilter = document.getElementById("status-filter");
const sortOrder = document.getElementById("sort-order");
const inquiryList = document.getElementById("inquiry-list");
const emptyMessage = document.getElementById("empty-message");
const inquiryCount = document.getElementById("inquiry-count");
const saveMessage = document.getElementById("save-message");

let inquiries = loadInquiries();

renderInquiries();

searchInput.addEventListener("input", renderInquiries);
statusFilter.addEventListener("change", renderInquiries);
sortOrder.addEventListener("change", renderInquiries);

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const createdAt = new Date();
  const inquiry = {
    id: Date.now(),
    name: nameInput.value.trim(),
    email: emailInput.value.trim(),
    content: contentInput.value.trim(),
    status: STATUS_OPEN,
    createdAt: createdAt.toISOString()
  };

  if (!inquiry.name || !inquiry.email || !inquiry.content) {
    return;
  }

  inquiries.unshift(inquiry);
  saveInquiries();
  renderInquiries();

  form.reset();
  nameInput.focus();
  showSaveMessage();
});

inquiryList.addEventListener("click", (event) => {
  const id = Number(event.target.dataset.id);

  if (event.target.classList.contains("delete-button")) {
    deleteInquiry(id);
    return;
  }

  if (event.target.classList.contains("status-button")) {
    toggleStatus(id);
  }
});

function loadInquiries() {
  const savedData = localStorage.getItem(STORAGE_KEY);

  if (!savedData) {
    return [];
  }

  try {
    const parsedData = JSON.parse(savedData);

    return parsedData.map((inquiry) => ({
      status: STATUS_OPEN,
      createdAt: null,
      ...inquiry
    }));
  } catch (error) {
    return [];
  }
}

function saveInquiries() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(inquiries));
}

function renderInquiries() {
  const filteredInquiries = getFilteredInquiries();
  const displayedInquiries = sortInquiriesByDate(filteredInquiries);

  inquiryList.innerHTML = "";
  inquiryCount.textContent = `${displayedInquiries.length}件`;
  emptyMessage.style.display = displayedInquiries.length === 0 ? "block" : "none";
  emptyMessage.textContent = hasActiveFilter()
    ? "該当する問い合わせはありません"
    : "まだ問い合わせは登録されていません。";

  displayedInquiries.forEach((inquiry) => {
    const isDone = inquiry.status === STATUS_DONE;
    const listItem = document.createElement("li");
    listItem.className = `inquiry-card ${isDone ? "is-done" : ""}`;

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
    date.textContent = `登録日時：${formatCreatedAt(inquiry.createdAt)}`;

    const statusBadge = document.createElement("span");
    statusBadge.className = `status-badge ${isDone ? "is-done" : "is-open"}`;
    statusBadge.textContent = inquiry.status;

    const actionArea = document.createElement("div");
    actionArea.className = "inquiry-actions";

    const statusButton = document.createElement("button");
    statusButton.className = `status-button ${isDone ? "is-done" : ""}`;
    statusButton.type = "button";
    statusButton.dataset.id = inquiry.id;
    statusButton.setAttribute("aria-pressed", String(isDone));
    statusButton.textContent = isDone ? "未対応に戻す" : "対応済みにする";

    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.type = "button";
    deleteButton.dataset.id = inquiry.id;
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
    const searchableText = `${inquiry.name} ${inquiry.email} ${inquiry.content}`.toLowerCase();
    const matchesKeyword = !keyword || searchableText.includes(keyword);
    const matchesStatus = selectedStatus === "all" || inquiry.status === selectedStatus;

    return matchesKeyword && matchesStatus;
  });
}

function sortInquiriesByDate(inquiriesToSort) {
  return inquiriesToSort.sort((first, second) => {
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

  return `${year}/${month}/${day} ${hours}:${minutes}`;
}

function hasActiveFilter() {
  return searchInput.value.trim() !== "" || statusFilter.value !== "all";
}

function toggleStatus(id) {
  inquiries = inquiries.map((inquiry) => {
    if (inquiry.id !== id) {
      return inquiry;
    }

    return {
      ...inquiry,
      status: inquiry.status === STATUS_DONE ? STATUS_OPEN : STATUS_DONE
    };
  });

  saveInquiries();
  renderInquiries();
}

function deleteInquiry(id) {
  const isConfirmed = window.confirm("本当に削除しますか？");

  if (!isConfirmed) {
    return;
  }

  inquiries = inquiries.filter((inquiry) => inquiry.id !== id);
  saveInquiries();
  renderInquiries();
}

function showSaveMessage() {
  saveMessage.classList.add("show");

  setTimeout(() => {
    saveMessage.classList.remove("show");
  }, 1800);
}
