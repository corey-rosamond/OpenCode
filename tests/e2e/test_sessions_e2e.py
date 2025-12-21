"""E2E tests for session management."""

import pytest


class TestSessionLifecycle:
    """E2E tests for session lifecycle."""

    def test_creates_session(self, session_manager):
        """Given session manager, creates new session"""
        session = session_manager.create(title="E2E Test Session")

        assert session is not None
        assert session.session_id is not None
        assert session.title == "E2E Test Session"
        assert len(session.messages) == 0

    def test_lists_sessions(self, session_manager):
        """Given created sessions, lists them"""
        # Create sessions
        session1 = session_manager.create(title="Session 1")
        session2 = session_manager.create(title="Session 2")

        # List sessions
        sessions = session_manager.list_sessions()

        assert len(sessions) >= 2
        session_ids = [s["id"] for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_loads_session(self, session_manager):
        """Given saved session, loads it back"""
        # Create and save
        original = session_manager.create(title="Load Test")
        original.add_user_message("Test message")
        session_manager.save()

        # Load
        loaded = session_manager.load(original.session_id)

        assert loaded is not None
        assert loaded.session_id == original.session_id
        assert loaded.title == original.title
        assert len(loaded.messages) == 1

    def test_deletes_session(self, session_manager):
        """Given session, deletes it successfully"""
        # Create session
        session = session_manager.create(title="Delete Me")
        session_id = session.session_id
        session_manager.save()

        # Delete
        session_manager.delete(session_id)

        # Verify deleted
        with pytest.raises(FileNotFoundError):
            session_manager.load(session_id)

    def test_updates_session_title(self, session_manager):
        """Given session, updates title"""
        session = session_manager.create(title="Original Title")
        session_id = session.session_id

        # Update title
        session.title = "Updated Title"
        session_manager.save()

        # Reload and verify
        loaded = session_manager.load(session_id)
        assert loaded.title == "Updated Title"


class TestSessionMessages:
    """E2E tests for session message handling."""

    def test_adds_user_message(self, session_manager):
        """Given session, adds user message"""
        session = session_manager.create(title="Message Test")

        session.add_user_message("Hello, assistant!")

        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello, assistant!"
        assert session.messages[0].role == "user"

    def test_adds_assistant_message(self, session_manager):
        """Given session, adds assistant message"""
        session = session_manager.create(title="Message Test")

        session.add_assistant_message("Hello, user!")

        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello, user!"
        assert session.messages[0].role == "assistant"

    def test_conversation_flow(self, session_manager):
        """Given session, handles full conversation"""
        session = session_manager.create(title="Conversation")

        # User message
        session.add_user_message("What is 2 + 2?")
        assert len(session.messages) == 1

        # Assistant response
        session.add_assistant_message("2 + 2 equals 4.")
        assert len(session.messages) == 2

        # User followup
        session.add_user_message("Thanks!")
        assert len(session.messages) == 3

        # Save and reload
        session_manager.save()
        loaded = session_manager.load(session.session_id)

        assert len(loaded.messages) == 3
        assert loaded.messages[0].role == "user"
        assert loaded.messages[1].role == "assistant"
        assert loaded.messages[2].role == "user"


class TestSessionPersistence:
    """E2E tests for session persistence."""

    def test_saves_session_to_disk(self, session_manager, forge_data_dir):
        """Given session, saves to disk"""
        session = session_manager.create(title="Persist Test")
        session.add_user_message("Test message")

        session_manager.save()

        # Verify file exists
        session_file = forge_data_dir / "sessions" / f"{session.session_id}.json"
        assert session_file.exists()

    def test_loads_from_disk_after_restart(self, session_manager, forge_data_dir):
        """Given saved session, loads after simulated restart"""
        # Create and save
        session = session_manager.create(title="Restart Test")
        session.add_user_message("Before restart")
        session_id = session.session_id
        session_manager.save()

        # Simulate restart by creating new manager
        from code_forge.sessions import SessionManager, SessionStorage

        storage = SessionStorage(forge_data_dir / "sessions")
        new_manager = SessionManager(storage=storage)

        # Load session
        loaded = new_manager.load(session_id)

        assert loaded is not None
        assert loaded.session_id == session_id
        assert loaded.title == "Restart Test"
        assert len(loaded.messages) == 1

    def test_handles_concurrent_sessions(self, session_manager):
        """Given multiple sessions, handles them independently"""
        session1 = session_manager.create(title="Session 1")
        session2 = session_manager.create(title="Session 2")

        session1.add_user_message("Message for session 1")
        session2.add_user_message("Message for session 2")

        assert len(session1.messages) == 1
        assert len(session2.messages) == 1
        assert session1.messages[0].content != session2.messages[0].content


class TestSessionCommands:
    """E2E tests for session-related commands."""

    @pytest.mark.asyncio
    async def test_session_new_command(self):
        """Given /session new command, creates new session"""
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext
        from code_forge.commands.builtin.session import SessionNewCommand

        cmd = SessionNewCommand()
        parsed = ParsedCommand(
            name="session-new",
            args=["Test Session"],
            raw="session-new Test Session",
        )
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert result.success
        assert "created" in result.output.lower() or "new session" in result.output.lower()

    @pytest.mark.asyncio
    async def test_session_list_command(self, session_manager):
        """Given /session list command, lists sessions"""
        from code_forge.commands.parser import ParsedCommand
        from code_forge.commands.executor import CommandContext
        from code_forge.commands.builtin.session import SessionListCommand

        # Create some sessions first
        session_manager.create(title="Test 1")
        session_manager.create(title="Test 2")
        session_manager.save()

        cmd = SessionListCommand()
        parsed = ParsedCommand(name="session-list", args=[], raw="session-list")
        context = CommandContext()

        result = await cmd.execute(parsed, context)

        assert result.success
        assert "Test 1" in result.output or "Test 2" in result.output
