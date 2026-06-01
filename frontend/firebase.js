import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyCZSUhuIh0WjvRfwkA_KZTIlMREphfr7gc",
  authDomain: "lab-1-c4539.firebaseapp.com",
  databaseURL: "https://lab-1-c4539-default-rtdb.firebaseio.com",
  projectId: "lab-1-c4539",
  storageBucket: "lab-1-c4539.firebasestorage.app",
  messagingSenderId: "848172289152",
  appId: "1:848172289152:web:1ab0766326e1fd48022a65",
  measurementId: "G-GE6Z478CGC"
};

export const firebaseConfigReady = Object.values(firebaseConfig).every(
  (value) => value && !value.startsWith("YOUR_")
);

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
