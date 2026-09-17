from scripts import search_game


def test_console_search_prompts_and_prints_results(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "Cyberpunk 2077")

    async def fake_search(query: str) -> None:
        print(f"searched:{query}")

    monkeypatch.setattr(search_game, "_search", fake_search)

    assert search_game.main() == 0
    assert "searched:Cyberpunk 2077" in capsys.readouterr().out


def test_console_search_rejects_empty_title(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "   ")
    assert search_game.main() == 2
    assert "required" in capsys.readouterr().err
