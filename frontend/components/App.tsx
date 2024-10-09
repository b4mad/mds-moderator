"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from 'next/navigation';

type State = "idle" | "launching" | "room_created" | "error";

type SpriteOption = {
  value: string;
  label: string;
};

const spriteOptions: SpriteOption[] = [
  { value: "parkingmeter", label: "Parking meter" },
  { value: "parkingmeter_banana", label: "Minion meter" },
  { value: "robot", label: "Robot" },
];

export default function App() {
  const [state, setState] = useState<State>("idle");
  const [room, setRoom] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string>(process.env.SYSTEM_PROMPT || "You are a friendly chatbot.");
  const [spriteFolderName, setSpriteFolderName] = useState<string>(spriteOptions[0].value);

  const searchParams = useSearchParams();

  useEffect(() => {
    const promptParam = searchParams.get('prompt');
    const spriteParam = searchParams.get('sprite');

    if (promptParam) {
      setSystemPrompt(decodeURIComponent(promptParam));
    }
    if (spriteParam) {
      const decodedSprite = decodeURIComponent(spriteParam);
      if (spriteOptions.some(option => option.value === decodedSprite)) {
        setSpriteFolderName(decodedSprite);
      }
    }
  }, [searchParams]);

  async function launchBot() {
    setState("launching");

    try {
      const response = await fetch("/start_bot", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          system_prompt: systemPrompt,
          sprite_folder: spriteFolderName || undefined
        }),
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
          <div>
            <label htmlFor="spriteSelect" className="block text-sm font-medium text-gray-900 bg-gray-100 p-1 rounded mb-1">
              Appearance
            </label>
            <select
              id="spriteSelect"
              value={spriteFolderName}
              onChange={(e) => setSpriteFolderName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded"
            >
              {spriteOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="systemPrompt" className="block text-sm font-medium text-gray-900 bg-gray-100 p-1 rounded mb-1">
              System Prompt
            </label>
            <textarea
              id="systemPrompt"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full h-32 p-2 border border-gray-300 rounded"
              placeholder="Enter system prompt..."
            />
          </div>
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
