const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ENDPOINT_BY_EXTENSION = {
  txt: "/translate-txt",
  epub: "/translate-epub",
  pdf: "/translate-pdf",
};

function extensionOf(filename) {
  const parts = filename.toLowerCase().split(".");
  return parts.length > 1 ? parts[parts.length - 1] : "";
}

export function endpointForFile(file) {
  const ext = extensionOf(file.name);
  const endpoint = ENDPOINT_BY_EXTENSION[ext];
  if (!endpoint) {
    throw new Error(`Formato no soportado: .${ext || "?"} (usa .txt, .epub o .pdf)`);
  }
  return endpoint;
}

async function readErrorDetail(response) {
  const body = await response.json().catch(() => ({}));
  return body.detail || `Error ${response.status}`;
}

export async function uploadFile(file) {
  const endpoint = endpointForFile(file);
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  const data = await response.json();
  return data.job_id;
}

export async function fetchStatus(jobId) {
  const response = await fetch(`${API_BASE_URL}/status/${jobId}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json();
}

export function downloadUrl(jobId) {
  return `${API_BASE_URL}/download/${jobId}`;
}
