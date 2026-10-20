import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from transcript import Transcript, markdown, matches


class TranscriptTests(unittest.TestCase):
    def test_tool_lifecycle_has_one_entry_and_authoritative_output(self):
        t = Transcript()
        t.item({'id': 'a', 'type': 'commandExecution', 'command': 'ls', 'status': 'inProgress'})
        t.delta({'itemId': 'a', 'delta': '\nfile'}, tool=True)
        final = {'id': 'a', 'type': 'commandExecution', 'command': 'ls', 'status': 'completed', 'aggregatedOutput': 'file'}
        t.item(final, True)
        t.item(final, True)
        t.delta({'itemId': 'a', 'delta': 'late'}, tool=True)
        text, _ = t.render()
        self.assertEqual(len(t.rows), 1)
        self.assertEqual(text.count('file'), 1)
        self.assertNotIn('late', text)

    def test_agent_stream_and_completion_share_message(self):
        t = Transcript()
        t.item({'id': 'a', 'type': 'agentMessage', 'text': ''})
        t.delta({'itemId': 'a', 'delta': '**Hello**'})
        t.item({'id': 'a', 'type': 'agentMessage', 'text': '**Hello** world'}, True)
        self.assertEqual(t.render()[0], 'Codex\nHello world\n\n')
        self.assertEqual(len(t.rows), 1)

    def test_markdown_code_headings_links_and_literal_markup(self):
        text, spans = markdown('# Title\n**Bold** `code` [site](https://example.org)\n```py\n**literal** <tag>\n```\n')
        self.assertEqual(text, 'Title\nBold code site (https://example.org)\n**literal** <tag>\n')
        self.assertTrue(any(text[a:b] == 'code' and tag == 'code' for tag, a, b in spans))
        self.assertTrue(any('**literal**' in text[a:b] and tag == 'code' for tag, a, b in spans))

    def test_search_literal_case_insensitive_unicode_offsets(self):
        self.assertEqual(matches('é A.b a.B', 'a.b'), [(2, 5), (6, 9)])
        self.assertEqual(matches('anything', ''), [])
        self.assertEqual(matches('anything', 'missing'), [])

    def test_presentation_is_bounded(self):
        t = Transcript()
        for i in range(1100):
            t.add('Tool', str(i), str(i))
        self.assertEqual(len(t.rows), 1000)
        self.assertNotIn('0', t.items)
        t.add('Codex', 'x' * 400000)
        self.assertLessEqual(sum(len(r['text']) for r in t.rows), 300000)


class SearchNavigationTests(unittest.TestCase):
    def test_navigation_wraps_both_directions_and_selects_offsets(self):
        from embedded_ui import EmbeddedView
        from unittest.mock import MagicMock
        view = EmbeddedView.__new__(EmbeddedView)
        view.output = MagicMock()
        view.search_count = MagicMock()
        view.search_hits = [(0, 3), (8, 11)]
        view.search_index = -1
        view.navigate(-1)
        self.assertEqual(view.search_index, 1)
        view.navigate(1)
        self.assertEqual(view.search_index, 0)
        view.navigate(1)
        self.assertEqual(view.search_index, 1)
        view.search_count.set_text.assert_called_with('2 / 2')
        self.assertEqual(view.output.get_buffer().select_range.call_count, 3)

    def test_empty_search_clears_highlights_and_disables_navigation(self):
        from embedded_ui import EmbeddedView
        from unittest.mock import MagicMock
        view = EmbeddedView.__new__(EmbeddedView)
        view.output = MagicMock()
        view.output.get_buffer().get_bounds.return_value = (0, 20)
        view.output.get_buffer().get_text.return_value = 'some text'
        view.search = MagicMock()
        view.search.get_text.return_value = ''
        view.previous, view.next, view.search_count = MagicMock(), MagicMock(), MagicMock()
        view.search_index = 4
        view.update_search()
        self.assertEqual(view.search_hits, [])
        self.assertEqual(view.search_index, -1)
        view.previous.set_sensitive.assert_called_with(False)
        view.next.set_sensitive.assert_called_with(False)
        view.output.get_buffer().remove_tag_by_name.assert_called_once()


class PresentationRegressionTests(unittest.TestCase):
    def test_output_before_start_and_late_start_use_one_tool_row(self):
        t = Transcript()
        t.delta({'itemId': 'cmd', 'delta': 'hello\n'}, tool=True)
        item = {'id': 'cmd', 'type': 'commandExecution', 'command': 'echo hello'}
        t.item(item)
        t.item(dict(item, aggregatedOutput='hello\n', exitCode=0), True)
        t.item(item)  # A delayed start cannot replace the completed summary.
        text, spans = t.render()
        self.assertEqual(len(t.rows), 1)
        self.assertEqual(text.count('hello\n'), 1)
        self.assertIn('done · exit 0', text)
        self.assertNotIn('commandExecution', text)
        self.assertTrue(any(tag == 'tool' for tag, _, _ in spans))

    def test_tool_preview_is_compact_and_not_markdown(self):
        t = Transcript()
        t.item({'id': 'cmd', 'type': 'commandExecution', 'command': '**literal**',
                'aggregatedOutput': '\n'.join(str(i) for i in range(100))}, True)
        text, _ = t.render()
        self.assertIn('**literal**', text)
        self.assertIn('output abbreviated', text)
        self.assertLess(len(text.splitlines()), 15)
        t.item({'id': 'raw', 'type': 'rawProtocolEvent', 'text': 'private noise'})
        self.assertEqual(len(t.rows), 1)

    def test_fences_preserve_blank_lines_and_nested_shorter_fences(self):
        text, spans = markdown('Paragraph one.\n\nParagraph two.\n\n````py\na = 1\n```\n\n````\n~~~\n<tag>\n~~~\n')
        self.assertEqual(text, 'Paragraph one.\n\nParagraph two.\n\na = 1\n```\n\n<tag>\n')
        self.assertTrue(all(0 <= a <= b <= len(text) for _, a, b in spans))

    def test_restored_history_and_live_items_render_identically(self):
        from embedded_ui import EmbeddedView
        from unittest.mock import MagicMock
        user = {'type': 'userMessage', 'content': [{'type': 'text', 'text': 'First\n\nSecond'}]}
        agent = {'id': 'agent', 'type': 'agentMessage', 'text': '**Answer**\n\n```py\nx = 1\n```'}
        tool = {'id': 'cmd', 'type': 'commandExecution', 'command': 'ls', 'status': 'completed', 'aggregatedOutput': 'one\ntwo'}
        live = Transcript()
        live.add('You', 'First\n\nSecond')
        live.item(dict(tool, status='inProgress', aggregatedOutput=''))
        live.delta({'itemId': 'cmd', 'delta': 'one\ntwo'}, tool=True)
        live.item(tool, True)
        live.delta({'itemId': 'agent', 'delta': '**Answer**'})
        live.item(agent, True)
        view = EmbeddedView.__new__(EmbeddedView)
        view.items, view.render = {}, MagicMock()
        view.event('history', {'turns': [{'items': [user, tool, agent]}]})
        self.assertEqual(view.transcript.render(), live.render())
        view.render.assert_called_once()


class ComposerLayoutTests(unittest.TestCase):
    def test_split_keeps_transcript_and_composer_minimums_and_actions_outside(self):
        from embedded_ui import EmbeddedView
        from unittest.mock import MagicMock, patch
        app = MagicMock()
        with patch('embedded_ui.Gtk') as gtk, patch.object(EmbeddedView, 'reconnect'), patch.object(EmbeddedView, 'update_search'):
            view = EmbeddedView(app, {}, 'one')
            split = gtk.Paned.return_value
            split.pack1.assert_called_once()
            split.pack2.assert_called_once()
            self.assertEqual(split.pack1.call_args.kwargs, {'resize': True, 'shrink': False})
            self.assertEqual(split.pack2.call_args.kwargs, {'resize': False, 'shrink': False})
            self.assertEqual(gtk.ScrolledWindow.call_count, 2)
            view.prompt.set_accepts_tab.assert_called_once_with(False)
            app.ai_controls.hide.assert_called_once()
            app.ai_advanced.hide.assert_called_once()

    def test_multiline_send_uses_buffer_and_preserves_validation(self):
        from embedded_ui import EmbeddedView
        from unittest.mock import MagicMock
        view = EmbeddedView.__new__(EmbeddedView)
        view.ready, view.working = True, False
        view.prompt, view.status, view.conversation = MagicMock(), MagicMock(), MagicMock()
        view.transcript, view.render, view.task = Transcript(), MagicMock(), MagicMock()
        buffer = view.prompt.get_buffer()
        buffer.get_bounds.return_value = (0, 10)
        buffer.get_text.return_value = 'First\n\nSecond'
        view.send()
        self.assertEqual(view.transcript.rows[0]['text'], 'First\n\nSecond')
        task, done = view.task.call_args.args
        task()
        view.conversation.send.assert_called_once_with('First\n\nSecond')
        done(None)
        buffer.set_text.assert_called_once_with('')
        view.task.reset_mock()
        buffer.get_text.return_value = 'x' * 32001
        view.send()
        view.task.assert_not_called()
        self.assertEqual(len(view.transcript.rows), 1)
