import { auth } from "./firebase.js";
import {
  signInWithEmailAndPassword,
  signOut
} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const loginBtn = document.getElementById("login");
const logoutBtn = document.getElementById("logout");
const sendBtn = document.getElementById("send");

loginBtn.onclick = async () => {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  await signInWithEmailAndPassword(auth, email, password);
  alert("Login success");
};

logoutBtn.onclick = async () => {
  await signOut(auth);
  alert("Logged out");
};

sendBtn.onclick = async () => {
  const msg = document.getElementById("msg").value;

  const res = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ message: msg })
  });

  const data = await res.json();

  document.getElementById("chat").innerHTML +=
    `<p>You: ${msg}</p><p>${data.reply}</p>`;
};

// load history
async function loadMessages() {
  const res = await fetch("http://127.0.0.1:8000/messages");
  const data = await res.json();

  data.forEach(m => {
    document.getElementById("chat").innerHTML +=
      `<p>You: ${m.user_message}</p><p>${m.bot_reply}</p>`;
  });
}

loadMessages();
