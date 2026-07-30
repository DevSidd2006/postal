import tempfile
import unittest
from pathlib import Path

from agent.agent import Agent
from agent.session import Session
from agent.store import SessionMeta, SessionStore, make_title
from client.response import StreamEvent, StreamEventType, TextDelta, TokenUsage
from config.config import Config
from context.manager import INTERRUPTED_TOOL_OUTPUT, ContextManager
from tools.subagents.subagents import CODEBASE_INVESTIGATOR, SubAgentTool


def make_meta(session_id: str = "session-1", cwd: str = "/proj", turns: int = 1) -> SessionMeta:
    return SessionMeta(
        session_id=session_id,
        cwd=cwd,
        model="anthropic/claude-sonnet-4.5",
        title="do the thing",
        turns=turns,
        usage={"total_tokens": 10},
    )


def message(role: str, content: str, **extra) -> dict:
    return {
        "role": role,
        "content": content,
        "token_count": len(content),
        "tool_call_id": None,
        "tool_calls": [],
        "pruned_at": None,
        **extra,
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = SessionStore(Path(tmp.name))

    def test_save_and_load_round_trip(self):
        messages = [message("user", "hello"), message("assistant", "hi")]

        checkpoint = self.store.save(make_meta(), messages)
        record = self.store.load("session-1")

        self.assertEqual(record.checkpoint.id, checkpoint.id)
        self.assertEqual(record.messages, messages)
        self.assertEqual(record.meta.title, "do the thing")
        self.assertEqual(record.meta.usage["total_tokens"], 10)

    def test_load_returns_none_for_unknown_session(self):
        self.assertIsNone(self.store.load("nope"))

    def test_each_checkpoint_keeps_its_own_transcript(self):
        first = self.store.save(make_meta(turns=1), [message("user", "one")])
        self.store.save(make_meta(turns=2), [message("user", "one"), message("user", "two")])

        rewound = self.store.load("session-1", first.id)
        head = self.store.load("session-1")

        self.assertEqual(len(rewound.messages), 1)
        self.assertEqual(len(head.messages), 2)
        self.assertEqual(head.meta.turns, 2)

    def test_listing_is_scoped_to_a_directory_and_newest_first(self):
        self.store.save(make_meta("a", cwd=str(Path.cwd())), [message("user", "a")])
        self.store.save(make_meta("b", cwd="/elsewhere"), [message("user", "b")])
        self.store.save(make_meta("c", cwd=str(Path.cwd())), [message("user", "c")])

        here = [meta.session_id for meta in self.store.list(Path.cwd())]

        self.assertEqual(set(here), {"a", "c"})
        self.assertEqual(len(self.store.list()), 3)
        self.assertEqual(self.store.list()[0].session_id, "c")

    def test_resolve_accepts_a_prefix_and_prefers_the_current_directory(self):
        self.store.save(make_meta("abc-other", cwd="/elsewhere"), [message("user", "x")])
        self.store.save(make_meta("abc-here", cwd=str(Path.cwd())), [message("user", "y")])

        self.assertEqual(self.store.resolve("abc-here"), "abc-here")
        self.assertEqual(self.store.resolve("abc", Path.cwd()), "abc-here")
        self.assertIsNone(self.store.resolve("zzz"))

    def test_trimming_drops_autosaves_before_named_checkpoints(self):
        kept = self.store.save(
            make_meta(),
            [message("user", "keep me")],
            label="milestone",
            auto=False,
            max_checkpoints=3,
        )
        for index in range(5):
            head = self.store.save(
                make_meta(turns=index),
                [message("user", f"turn {index}")],
                max_checkpoints=3,
            )

        meta = self.store.read_meta("session-1")
        ids = [checkpoint.id for checkpoint in meta.checkpoints]

        self.assertEqual(len(ids), 3)
        self.assertIn(kept.id, ids)
        self.assertEqual(ids[-1], head.id)
        # Trimmed transcripts are gone from the JSONL too, not just the listing.
        self.assertEqual(len(list(self.store._iter_records("session-1"))), 3)
        self.assertIsNotNone(self.store.load("session-1", kept.id))

    def test_delete_and_prune(self):
        for name in ("a", "b", "c"):
            self.store.save(make_meta(name), [message("user", name)])

        self.assertTrue(self.store.delete("a"))
        self.assertFalse(self.store.delete("a"))
        self.assertEqual(self.store.prune(1), 1)
        self.assertEqual(len(self.store.list()), 1)

    def test_title_is_a_single_trimmed_line(self):
        self.assertEqual(make_title("  fix   the\nbug "), "fix the bug")
        self.assertTrue(make_title("x" * 200).endswith("…"))
        self.assertLessEqual(len(make_title("x" * 200)), 72)

    def _save_with_limit(self, limit: int) -> None:
        self.store.save(make_meta(), [message("user", "x")], max_checkpoints=limit)

    def test_checkpoint_limit_is_respected(self):
        for _ in range(10):
            self._save_with_limit(3)

        self.assertEqual(len(self.store.read_meta("session-1").checkpoints), 3)


class ContextRoundTripTests(unittest.TestCase):
    def _manager(self) -> ContextManager:
        return ContextManager(Config(), user_memory=None, tools=[])

    def test_export_restore_preserves_the_conversation(self):
        manager = self._manager()
        manager.add_user_message("write a test")
        manager.add_assistant_message(
            "on it",
            [{"id": "call-1", "type": "function", "function": {"name": "read", "arguments": "{}"}}],
        )
        manager.add_tool_result("call-1", "file contents")

        exported = manager.export_messages()

        restored = self._manager()
        restored.restore_messages(exported)

        self.assertEqual(restored.get_messages(), manager.get_messages())
        self.assertEqual(restored.message_count, 3)

    def test_restore_seeds_usage_so_pruning_has_a_baseline(self):
        manager = self._manager()
        manager.restore_messages([message("user", "hello"), message("assistant", "hi")])

        self.assertEqual(manager._latest_usage.total_tokens, len("hello") + len("hi"))

    def test_restore_answers_tool_calls_left_hanging_by_an_interrupt(self):
        manager = self._manager()
        manager.add_user_message("read the file")
        manager.add_assistant_message(
            None,
            [
                {"id": "call-1", "type": "function", "function": {"name": "read", "arguments": "{}"}},
                {"id": "call-2", "type": "function", "function": {"name": "grep", "arguments": "{}"}},
            ],
        )
        manager.add_tool_result("call-1", "the file")

        # Interrupted right there: call-2 never got a result.
        resumed = self._manager()
        resumed.restore_messages(manager.export_messages())

        messages = resumed.get_messages()
        answered = [item["tool_call_id"] for item in messages if item["role"] == "tool"]

        self.assertEqual(answered, ["call-1", "call-2"])
        self.assertEqual(messages[-1]["content"], INTERRUPTED_TOOL_OUTPUT)
        # A transcript that is already whole is left alone.
        self.assertEqual(resumed.answer_dangling_tool_calls(), 0)

    def test_clear_resets_usage(self):
        manager = self._manager()
        manager.restore_messages([message("user", "hello")])
        manager.clear()

        self.assertEqual(manager.message_count, 0)
        self.assertEqual(manager._latest_usage.total_tokens, 0)


class SessionCheckpointTests(unittest.TestCase):
    def _session(self) -> Session:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        config = Config()
        session = Session(config)
        session.store = SessionStore(Path(tmp.name))
        session.context_manager = ContextManager(config, user_memory=None, tools=[])
        return session

    def test_a_turn_is_saved_and_can_be_resumed(self):
        session = self._session()
        session.note_prompt("add session checkpoints")
        session.inc_turn()
        session.context_manager.add_user_message("add session checkpoints")
        session.context_manager.add_assistant_message("done")
        session.context_manager.add_usage(TokenUsage(prompt_tokens=5, total_tokens=7))

        checkpoint = session.save_checkpoint()
        self.assertIsNotNone(checkpoint)

        resumed = self._session()
        resumed.store = session.store
        record = resumed.resume(session.session_id[:8])

        self.assertIsNotNone(record)
        self.assertEqual(resumed.session_id, session.session_id)
        self.assertEqual(resumed.title, "add session checkpoints")
        self.assertEqual(resumed.turns, 1)
        self.assertEqual(resumed.context_manager.message_count, 2)
        self.assertEqual(resumed.context_manager.total_usage.total_tokens, 7)

    def test_nothing_to_save_writes_nothing(self):
        session = self._session()

        self.assertIsNone(session.save_checkpoint())
        self.assertEqual(session.store.list(), [])

    def test_autosave_does_not_duplicate_an_unchanged_transcript(self):
        session = self._session()
        session.context_manager.add_user_message("hello")

        self.assertIsNotNone(session.save_checkpoint())
        self.assertIsNone(session.save_checkpoint())

        # An explicitly requested checkpoint is always written.
        self.assertIsNotNone(session.save_checkpoint(label="mine", auto=False))
        self.assertEqual(len(session.checkpoints()), 2)

    def test_disabled_sessions_never_touch_disk(self):
        session = self._session()
        session.config.session.enabled = False
        session.context_manager.add_user_message("hello")

        self.assertIsNone(session.save_checkpoint())
        self.assertEqual(session.store.list(), [])

    def test_resuming_an_unknown_session_leaves_the_current_one_alone(self):
        session = self._session()
        session.context_manager.add_user_message("hello")
        session_id = session.session_id

        self.assertIsNone(session.resume("does-not-exist"))
        self.assertEqual(session.session_id, session_id)
        self.assertEqual(session.context_manager.message_count, 1)

    def test_rewind_restores_an_earlier_checkpoint(self):
        session = self._session()
        session.inc_turn()
        session.context_manager.add_user_message("first")
        first = session.save_checkpoint(label="first", auto=False)

        session.inc_turn()
        session.context_manager.add_user_message("second")
        session.save_checkpoint()

        record = session.store.load(session.session_id, first.id)
        session.restore(record)

        self.assertEqual(session.context_manager.message_count, 1)
        self.assertEqual(session.turns, 1)

    def test_reset_starts_a_new_session_and_leaves_the_old_one_saved(self):
        session = self._session()
        session.note_prompt("the old work")
        session.inc_turn()
        session.context_manager.add_user_message("the old work")
        session.save_checkpoint()
        old_id = session.session_id

        session.reset()

        self.assertNotEqual(session.session_id, old_id)
        self.assertEqual(session.turns, 0)
        self.assertEqual(session.context_manager.message_count, 0)
        self.assertTrue(session.store.exists(old_id))
        self.assertIsNotNone(session.resume(old_id))

    def test_new_sessions_prune_the_oldest(self):
        session = self._session()
        session.config.session.max_sessions = 2

        for index in range(4):
            session.session_id = f"session-{index}"
            session._saved_signature = None
            session.context_manager.add_user_message(f"turn {index}")
            session.save_checkpoint()

        self.assertEqual(len(session.store.list()), 2)


class AgentAutosaveTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_completed_turn_is_checkpointed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        async def reply(*args, **kwargs):
            yield StreamEvent(
                type=StreamEventType.MESSAGE_COMPLETE,
                text_delta=TextDelta("all done"),
                usage=TokenUsage(prompt_tokens=12, completion_tokens=3, total_tokens=15),
            )

        config = Config(cwd=Path.cwd())
        async with Agent(config) as agent:
            agent.session.store = SessionStore(Path(tmp.name))
            agent.session.client.chat_completion = reply

            async for _ in agent.run("summarise the repo"):
                pass

            saved = agent.session.store.list()
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].title, "summarise the repo")
            self.assertEqual(saved[0].turns, 1)

            record = agent.session.store.load(saved[0].session_id)
            self.assertEqual([item["role"] for item in record.messages], ["user", "assistant"])

    async def test_subagent_runs_are_not_saved(self):
        config = Config(cwd=Path.cwd())
        tool = SubAgentTool(config, CODEBASE_INVESTIGATOR)

        self.assertTrue(config.session.enabled)
        self.assertFalse(tool.subagent_config().session.enabled)


if __name__ == "__main__":
    unittest.main()
