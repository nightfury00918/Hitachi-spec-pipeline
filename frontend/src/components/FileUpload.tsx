// src/components/FileUpload.tsx
import { useState, useRef } from "react";
import { processFiles, uploadFiles } from "../services/api";

interface FileUploadProps {
  onUploaded: () => void;
}

export default function FileUpload({ onUploaded }: FileUploadProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleUpload = async () => {
    if (!files.length) return alert("Select files first");
    setLoading(true);
    try {
      const fileMetadata = await uploadFiles(files);
      await processFiles(fileMetadata);
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded();
    } catch (err) {
      console.error("Upload failed", err);
      alert("Upload or processing failed: " + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 border rounded-lg shadow bg-white">
      <h2 className="text-xl font-bold mb-2">📂 Upload Documents</h2>
      <input
        ref={inputRef}
        type="file"
        multiple
        className="mb-3"
        onChange={(e) =>
          setFiles(e.target.files ? Array.from(e.target.files) : [])
        }
      />
      <div className="flex items-center space-x-2">
        <button
          onClick={handleUpload}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-black rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Uploading & Processing..." : "Upload & Process"}
        </button>
        <div className="text-sm text-gray-600">
          {files.length ? `${files.length} selected` : "No files selected"}
        </div>
      </div>
    </div>
  );
}
