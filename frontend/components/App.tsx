"use client";

import React, { useState } from "react";

type State = "idle" | "launching" | "room_created" | "error";

export default function App() {
  const [state, setState] = useState<State>("idle");
  const [room, setRoom] = useState<string | null>(null);

  async function launchBot() {
    setState("launching");

    try {
      const response = await fetch("/start_bot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const { room_url } = await response.json();

      setRoom(room_url);
      setState("room_created");
    } catch (error) {
      console.error("Error launching bot:", error);
      setState("error");
    }
  }

  if (state === "error") {
    return (
      <div className="flex items-center mx-auto">
        <p className="text-red-500 font-semibold bg-white px-4 py-2 shadow-xl rounded-lg">
          An error occurred. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-4">
      {state === "idle" && (
        <button
          onClick={launchBot}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Launch Bot
        </button>
      )}
      {state === "launching" && <p>Launching bot...</p>}
      {state === "room_created" && (
        <>
          <p>Room created successfully!</p>
          <a
            href={room || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-700 underline"
          >
            {room}
          </a>
        </>
      )}
    </div>
  );
}
