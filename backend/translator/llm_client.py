import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import anthropic
import httpx

_DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
_DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5-20251001"
_CLAUDE_MAX_OUTPUT_TOKENS = 4096

_BASE_SYSTEM_PROMPT = (
    "Eres un traductor profesional. Traduce el siguiente texto de inglés a "
    "español. Devuelve ÚNICAMENTE la traducción, sin explicaciones, notas, "
    "comillas ni ningún texto adicional."
)


class TranslationError(Exception):
    """Domain error for translation failures, regardless of the provider."""


@dataclass
class TranslationResult:
    text: str
    input_tokens: int
    output_tokens: int


class TranslatorClient(ABC):
    @abstractmethod
    def translate(
        self,
        text: str,
        context: str | None = None,
        glossary: dict | None = None,
    ) -> TranslationResult:
        ...

    def close(self) -> None:
        """Release any resources held by the client. No-op by default."""


# NOTE: prompt_builder.build_translation_request() can already fold glossary
# instructions into the `context` string it returns. If a caller passes that
# already-formatted context here AND also passes `glossary`, the glossary
# instructions will be duplicated in the final prompt. For now, callers that
# go through prompt_builder must call translate() with glossary=None — see
# the README's "Checklist de seguridad pendiente por fase" / Fase 2 note for
# the plan to remove this implicit rule.
def _build_system_prompt(context: str | None, glossary: dict | None) -> str:
    parts = [_BASE_SYSTEM_PROMPT]

    if glossary:
        terms = "\n".join(f"- {es} -> {en}" for es, en in glossary.items())
        parts.append(
            "Usa exactamente estas traducciones para los siguientes términos, "
            "sin importar el contexto:\n" + terms
        )

    if context:
        parts.append(f"Contexto adicional para esta traducción: {context}")

    return "\n\n".join(parts)


class OllamaTranslator(TranslatorClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 120.0,
    ):
        self.base_url = (
            base_url or os.environ.get("OLLAMA_BASE_URL") or _DEFAULT_OLLAMA_BASE_URL
        ).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or _DEFAULT_OLLAMA_MODEL
        self._read_timeout = read_timeout
        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=connect_timeout,
                pool=connect_timeout,
            )
        )

    def translate(
        self,
        text: str,
        context: str | None = None,
        glossary: dict | None = None,
    ) -> TranslationResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _build_system_prompt(context, glossary)},
                {"role": "user", "content": text},
            ],
            "stream": False,
        }

        try:
            response = self._client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise TranslationError(
                f"No se pudo conectar con Ollama en {self.base_url}. "
                "¿Está corriendo 'ollama serve'?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TranslationError(
                f"Ollama no respondió en {self._read_timeout}s."
            ) from exc

        if response.status_code != 200:
            raise TranslationError(
                f"Ollama devolvió un error ({response.status_code}): {response.text}"
            )

        try:
            data = response.json()
            translated = data["message"]["content"]
        except (ValueError, KeyError) as exc:
            raise TranslationError(
                "Respuesta inesperada de Ollama: falta 'message.content'."
            ) from exc

        return TranslationResult(
            text=translated.strip(),
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )

    def close(self) -> None:
        self._client.close()


class ClaudeTranslator(TranslatorClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise TranslationError(
                "Falta ANTHROPIC_API_KEY en el entorno para usar ClaudeTranslator."
            )

        self.model = model or os.environ.get("ANTHROPIC_MODEL") or _DEFAULT_CLAUDE_MODEL
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    def translate(
        self,
        text: str,
        context: str | None = None,
        glossary: dict | None = None,
    ) -> TranslationResult:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=_CLAUDE_MAX_OUTPUT_TOKENS,
                system=_build_system_prompt(context, glossary),
                messages=[{"role": "user", "content": text}],
            )
        except anthropic.APIConnectionError as exc:
            raise TranslationError(
                f"No se pudo conectar con la API de Anthropic: {exc}"
            ) from exc
        except anthropic.APITimeoutError as exc:
            raise TranslationError(
                f"La API de Anthropic no respondió en {self._client.timeout}s."
            ) from exc
        except anthropic.AuthenticationError as exc:
            raise TranslationError(
                "ANTHROPIC_API_KEY inválida o sin permisos."
            ) from exc
        except anthropic.APIStatusError as exc:
            raise TranslationError(
                f"La API de Anthropic devolvió un error: {exc}"
            ) from exc

        translated = "".join(
            block.text for block in response.content if block.type == "text"
        )

        return TranslationResult(
            text=translated.strip(),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def close(self) -> None:
        self._client.close()


def get_translator() -> TranslatorClient:
    provider = os.environ.get("TRANSLATOR_PROVIDER", "ollama").strip().lower()

    if provider == "ollama":
        return OllamaTranslator()
    if provider == "claude":
        return ClaudeTranslator()

    raise ValueError(
        f"TRANSLATOR_PROVIDER desconocido: {provider!r}. "
        "Valores válidos: 'ollama', 'claude'."
    )
