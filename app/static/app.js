const ingestButton = document.querySelector("#ingestButton");
const statusBox = document.querySelector("#status");
const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const questionInput = document.querySelector("#question");

function setBusy(isBusy) {
  ingestButton.disabled = isBusy;
  chatForm.querySelector("button").disabled = isBusy;
}

function setStatus(text, isError = false) {
  statusBox.textContent = text;
  statusBox.classList.toggle("error", isError);
}

function addMessage(role, text, citations = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.textContent = text;

  if (citations.length > 0) {
    const list = document.createElement("div");
    list.className = "citations";
    citations.forEach((citation, index) => {
      const item = document.createElement("div");
      item.className = "citation";
      const link = document.createElement("a");
      link.href = citation.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = `[${index + 1}] ${citation.title}`;
      item.append(link, document.createTextNode(` - ${citation.source}`));
      if (citation.snippet) {
        item.append(document.createElement("br"), document.createTextNode(citation.snippet));
      }
      list.append(item);
    });
    article.append(list);
  }

  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

async function postJson(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

ingestButton.addEventListener("click", async () => {
  setBusy(true);
  setStatus("Ingesting and indexing news...");
  try {
    const result = await postJson("/api/ingest");
    setStatus(`${result.message} Source: ${result.source}.`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    setBusy(false);
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  addMessage("user", question);
  questionInput.value = "";
  setBusy(true);
  try {
    const result = await postJson("/api/chat", { question });
    addMessage("assistant", result.answer, result.citations);
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    setBusy(false);
  }
});
