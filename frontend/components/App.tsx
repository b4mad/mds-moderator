"use client";

import React, { useState } from "react";

type State = "idle" | "launching" | "room_created" | "error";

export default function App() {
  const [state, setState] = useState<State>("idle");
  const [room, setRoom] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string>("Du bist Chuck Norris");

  async function launchBot() {
    setState("launching");

    try {
      const response = await fetch("/start_bot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ system_prompt: systemPrompt }),
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
      <div className="flex items-center justify-center h-screen">
        <p className="text-red-500 font-semibold bg-white px-4 py-2 shadow-xl rounded-lg">
          An error occurred. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-screen w-full">
      {state === "idle" && (
        <div className="w-full max-w-4xl px-4 space-y-4">
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="w-full h-32 p-2 border border-gray-300 rounded"
            placeholder="Enter system prompt..."
          />
          <div className="flex justify-center">
            <button
              onClick={launchBot}
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
              Launch Bot
            </button>
          </div>
        </div>
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
