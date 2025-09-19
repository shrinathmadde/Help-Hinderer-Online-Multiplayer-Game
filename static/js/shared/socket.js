// static/js/shared/socket.js
let socket;

/** Single shared Socket.IO instance across the app. */
export function getSocket() {
  if (!socket) {
    socket = io();              // uses global io() from socket.io script tag
    window.socket = socket;     // helpful for console debugging
  }
  return socket;
}
