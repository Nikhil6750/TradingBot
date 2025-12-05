import { Plus, MoreHorizontal } from "lucide-react";

export default function ChatInput({ value, setValue, onSend }) {
  return (
    <div className="w-full border-t border-neutral-800 bg-[#0f0f0f] p-4">
      <div className="max-w-3xl mx-auto flex items-center rounded-full bg-neutral-900 border border-neutral-700 px-3 py-2">
        {/* Left + Button */}
        <button className="p-2 text-neutral-400 hover:text-white">
          <Plus className="w-5 h-5" />
        </button>

        {/* Input field */}
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && onSend()}
          placeholder="Ask anything"
          className="flex-1 bg-transparent outline-none px-3 text-neutral-200 placeholder-neutral-500 text-[15px]"
        />

        {/* Right … Button */}
        <button className="p-2 text-neutral-400 hover:text-white">
          <MoreHorizontal className="w-5 h-5" />
        </button>
      </div>

      {/* Send Button */}
      <div className="flex justify-end mt-3">
        <button
          onClick={onSend}
          className="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-md font-medium transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}
