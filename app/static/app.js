const ingestButton = document.querySelector("#ingestButton");
const statusBox = document.querySelector("#status");
const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const questionInput = document.querySelector("#question");

function setBusy(isBusy) {
  ingestButton.disabled = isBusy;
  chatForm.querySelector("button").disabled = isBusy;
  ingestButton.textContent = isBusy ? "Ingesting..." : "Ingest news";
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

function resetMessages(text) {
  messages.innerHTML = "";
  addMessage("assistant", text);
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
  const startedAt = new Date();
  setBusy(true);
  setStatus(`Starting fresh ingest at ${startedAt.toLocaleTimeString()}...`);
  resetMessages("Refreshing the vector store with the latest ingest...");
  try {
    const result = await postJson("/api/ingest");
    const title = result.article_titles?.[0] ? ` Article: ${result.article_titles[0]}.` : "";
    const elapsed = ((Date.now() - startedAt.getTime()) / 1000).toFixed(1);
    setStatus(`${result.message} Source: ${result.source}. Run: ${result.run_id}. Completed in ${elapsed}s at ${new Date(result.ingested_at).toLocaleTimeString()}.${title}`);
    resetMessages("Fresh ingest complete. Ask a question about the indexed article.");
  } catch (error) {
    setStatus(error.message, true);
    resetMessages("Ingest failed. Check the status message above.");
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
    addMessage("assistant", result.answer, result.sources || result.citations || []);
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    setBusy(false);
  }
});
