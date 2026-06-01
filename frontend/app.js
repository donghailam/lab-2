import { auth, firebaseConfigReady } from "./firebase.js";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut
} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const API_BASE_URL = window.location.port === "8000" ? window.location.origin : "http://localhost:8000";

const loginForm = document.getElementById("login-form");
const chatForm = document.getElementById("chat-form");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const messageInput = document.getElementById("message");
const loginButton = document.getElementById("login");
const logoutButton = document.getElementById("logout");
const reloadButton = document.getElementById("reload-history");
const authHint = document.getElementById("auth-hint");
const userEmail = document.getElementById("user-email");
const userUid = document.getElementById("user-uid");
const chatBox = document.getElementById("chat");
const statusBox = document.getElementById("status");
const composerButton = document.getElementById("composer");

let chatHistory = [];

function setStatus(message, type = "info") {
  statusBox.textContent = message;
  statusBox.dataset.type = type;
}

function clearMessages() {
  chatBox.innerHTML = "";
}

function appendMessage(label, value, tone) {
  const article = document.createElement("article");
  article.className = `message ${tone}`;

  const title = document.createElement("strong");
  title.textContent = label;

  const content = document.createElement("p");
  content.textContent = value;

  article.append(title, content);
  chatBox.appendChild(article);
}

function renderMessages(messages) {
  clearMessages();

  if (!messages.length) {
    const emptyState = document.createElement("p");
    emptyState.className = "empty-state";
    emptyState.textContent = "No chat history yet. Send your first message.";
    chatBox.appendChild(emptyState);
    return;
  }

  messages.forEach((item) => {
    appendMessage("You", item.user_message, "user");
    appendMessage("Bot", item.bot_reply, "bot");
  });

  chatBox.scrollTop = chatBox.scrollHeight;
}

async function callApi(path, options = {}) {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("Please sign in first.");
  }

  const token = await user.getIdToken();
  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
    ...options.headers
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed.");
  }
  return payload;
}

async function refreshProfile() {
  const profile = await callApi("/auth/me", { method: "GET" });
  userEmail.textContent = profile.email || "No email";
  userUid.textContent = profile.uid;
}

async function refreshMessages() {
  const data = await callApi("/messages?limit=50", { method: "GET" });
  chatHistory = data.messages || [];
  renderMessages(chatHistory);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!firebaseConfigReady) {
    setStatus("Update frontend/firebase.js with your Firebase web app config first.", "error");
    return;
  }

  loginButton.disabled = true;
  setStatus("Signing in...", "info");

  try {
    await signInWithEmailAndPassword(auth, emailInput.value.trim(), passwordInput.value);
    setStatus("Signed in successfully.", "success");
    loginForm.reset();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    loginButton.disabled = false;
  }
});

logoutButton.addEventListener("click", async () => {
  try {
    await signOut(auth);
    setStatus("Signed out.", "info");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    setStatus("Message must not be empty.", "error");
    return;
  }

  try {
    composerButton.disabled = true;
    setStatus("Sending message...", "info");
    const data = await callApi("/chat", {
      method: "POST",
      body: JSON.stringify({ message })
    });
    chatHistory = [...chatHistory, data.message];
    renderMessages(chatHistory);
    messageInput.value = "";
    setStatus("Message saved to Firestore.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    composerButton.disabled = false;
  }
});

reloadButton.addEventListener("click", async () => {
  try {
    setStatus("Loading history...", "info");
    await refreshMessages();
    setStatus("History loaded.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});

onAuthStateChanged(auth, async (user) => {
  const loggedIn = Boolean(user);

  logoutButton.disabled = !loggedIn;
  composerButton.disabled = !loggedIn;
  reloadButton.disabled = !loggedIn;

  if (!loggedIn) {
    authHint.textContent = "Sign in with Firebase Email/Password to start chatting.";
    userEmail.textContent = "Not signed in";
    userUid.textContent = "-";
    chatHistory = [];
    clearMessages();
    setStatus(
      firebaseConfigReady ? "Waiting for login." : "Firebase client config is still using placeholders.",
      firebaseConfigReady ? "info" : "error"
    );
    return;
  }

  authHint.textContent = "Authenticated with Firebase. Backend requests are verified with your ID token.";

  try {
    await refreshProfile();
    await refreshMessages();
    setStatus("Ready.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
});
