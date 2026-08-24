import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from instagram_archive import ArchiveError, InstagramArchive
from instagram_archive.search import anonymize, search
from instagram_archive.web import Handler


def make_zip(files: dict[str, str | bytes]) -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    handle.close()
    path = Path(handle.name)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


class ImporterTests(unittest.TestCase):
    def tearDown(self) -> None:
        for path in getattr(self, "paths", []):
            path.unlink(missing_ok=True)

    def keep(self, path: Path) -> Path:
        self.paths = getattr(self, "paths", []) + [path]
        return path

    def test_json_unicode_attachment_and_search(self) -> None:
        payload = {"participants": [{"name": "João"}, {"name": "Lia"}], "title": "Café ☕", "messages": [
            {"sender_name": "João", "timestamp_ms": 1704067200000, "content": "Olá, reunião amanhã", "photos": [{"uri": "media/foto.jpg"}]},
            {"sender_name": "Lia", "timestamp_ms": 1704153600000, "content": "Combinado"},
        ]}
        path = self.keep(make_zip({"messages/inbox/cafe/message_1.json": json.dumps(payload, ensure_ascii=False), "media/foto.jpg": b"synthetic"}))
        with InstagramArchive(path) as archive:
            conversation = archive.conversations[0]
            self.assertEqual(conversation.title, "Café ☕")
            self.assertTrue(conversation.messages[0].attachments[0].exists)
            self.assertEqual(len(search(archive.conversations, name="joão", keyword="reunião", start=date(2024, 1, 1))), 1)

    def test_missing_attachment_is_recorded(self) -> None:
        payload = {"participants": [{"name": "Ana"}], "messages": [{"sender_name": "Ana", "timestamp_ms": 1, "content": "teste", "files": [{"uri": "media/ausente.pdf"}]}]}
        path = self.keep(make_zip({"messages/inbox/ana/message_1.json": json.dumps(payload)}))
        with InstagramArchive(path) as archive:
            attachment = archive.conversations[0].messages[0].attachments[0]
            self.assertFalse(attachment.exists)
            self.assertEqual(attachment.original_path, "media/ausente.pdf")

    def test_search_includes_bounded_chronological_context(self) -> None:
        payload = {"participants": [{"name": "Mayara"}], "messages": [
            {"sender_name": "Mayara", "timestamp_ms": 3000, "content": "depois"},
            {"sender_name": "Eu", "timestamp_ms": 1000, "content": "antes"},
            {"sender_name": "Mayara", "timestamp_ms": 2000, "content": "termo central"},
        ]}
        path = self.keep(make_zip({"messages/inbox/conversa/message_1.json": json.dumps(payload)}))
        with InstagramArchive(path) as archive:
            result = search(archive.conversations, keyword="termo", context=20)[0]
            self.assertEqual([message.text for message in result.before], ["antes"])
            self.assertEqual([message.text for message in result.after], ["depois"])

    def test_investigative_handle_search_checks_all_exported_fields(self) -> None:
        payload = {"participants": [{"name": "Instagram User"}], "title": "Conta removida", "messages": [
            {"sender_name": "Eu", "timestamp_ms": 1000, "content": "perfil antigo: @Máyara.ssnchess"},
            {"sender_name": "Instagram User", "timestamp_ms": 2000, "content": "outra mensagem"},
        ]}
        path = self.keep(make_zip({"messages/inbox/mayarassnchess_123/message_1.json": json.dumps(payload)}))
        with InstagramArchive(path) as archive:
            results = search(archive.conversations, name="@mayara_ssnchess")
            self.assertEqual(len(results), 2)
            self.assertIn("arquivo de origem", results[0].matched_in)
            self.assertTrue(any("texto" in result.matched_in for result in results))

    def test_html_export(self) -> None:
        page = '<html><body><div class="pam"><div>Maria</div><div>Olá do HTML</div><div>Jan 02, 2024 03:04 PM</div></div></body></html>'
        path = self.keep(make_zip({"messages/inbox/maria/message_1.html": page}))
        with InstagramArchive(path) as archive:
            self.assertEqual(archive.conversations[0].messages[0].sender, "Maria")
            self.assertIn("Olá do HTML", archive.conversations[0].messages[0].text)

    def test_zip_slip_and_executable_are_rejected(self) -> None:
        for member in ("../escape.json", "messages/inbox/payload.exe"):
            path = self.keep(make_zip({member: "synthetic"}))
            with self.assertRaises(ArchiveError):
                InstagramArchive(path).load()

    def test_anonymization(self) -> None:
        source = "CPF 123.456.789-00, email ana@example.com, tel (11) 99999-8888, Rua Flores, 10"
        clean = anonymize(source)
        self.assertNotIn("123.456", clean)
        self.assertNotIn("ana@", clean)
        self.assertIn("[TELEFONE]", clean)
        self.assertIn("[ENDEREÇO]", clean)

    def test_home_explains_phone_access_limits_and_safe_review(self) -> None:
        page = Handler._upload()
        self.assertIn("Comece agora por aqui", page)
        self.assertIn(".zip sem descompactá-lo", page)
        self.assertIn("aguarde o download terminar", page)
        self.assertIn("não consegue entrar, navegar ou examinar seu celular sozinho", page)
        self.assertIn("Configurações → Armazenamento", page)
        self.assertIn("Armazenamento do iPhone", page)
        self.assertIn("senha, PIN, token", page)


if __name__ == "__main__":
    unittest.main()
