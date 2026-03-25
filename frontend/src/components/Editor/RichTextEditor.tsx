import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Highlight from '@tiptap/extension-highlight';
import Underline from '@tiptap/extension-underline';
import { useCallback, useEffect } from 'react';

interface RichTextEditorProps {
  onSelectionChange: (text: string) => void;
  onContentChange: (content: string) => void;
  initialContent?: string;
}

export default function RichTextEditor({
  onSelectionChange,
  onContentChange,
  initialContent,
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        codeBlock: { HTMLAttributes: { class: 'code-block' } },
      }),
      Placeholder.configure({
        placeholder: 'Start writing your document…',
      }),
      Highlight.configure({ multicolor: false }),
      Underline,
    ],
    content: initialContent || '',
    onUpdate: ({ editor }) => {
      onContentChange(editor.getText());
    },
    onSelectionUpdate: ({ editor }) => {
      const { from, to } = editor.state.selection;
      if (from !== to) {
        const text = editor.state.doc.textBetween(from, to, ' ');
        onSelectionChange(text);
      } else {
        onSelectionChange('');
      }
    },
  });

  // Expose editor instance for external updates
  useEffect(() => {
    if (editor && initialContent && editor.isEmpty) {
      editor.commands.setContent(initialContent);
    }
  }, [editor, initialContent]);

  const replaceSelection = useCallback(
    (newText: string) => {
      if (!editor) return;
      const { from, to } = editor.state.selection;
      if (from !== to) {
        editor.chain().focus().deleteRange({ from, to }).insertContentAt(from, newText).run();
      }
    },
    [editor]
  );

  // Make replaceSelection available via window for sidebar interaction
  useEffect(() => {
    (window as any).__editorReplaceSelection = replaceSelection;
    return () => {
      delete (window as any).__editorReplaceSelection;
    };
  }, [replaceSelection]);

  return (
    <>
      <EditorToolbar editor={editor} />
      <div className="editor-content">
        <EditorContent editor={editor} />
      </div>
    </>
  );
}

// ─── Inline Toolbar Component ────────────────────────────────────────
function EditorToolbar({ editor }: { editor: any }) {
  if (!editor) return null;

  const groups = [
    [
      { label: 'B', command: () => editor.chain().focus().toggleBold().run(), active: editor.isActive('bold') },
      { label: 'I', command: () => editor.chain().focus().toggleItalic().run(), active: editor.isActive('italic'), style: { fontStyle: 'italic' } },
      { label: 'U', command: () => editor.chain().focus().toggleUnderline().run(), active: editor.isActive('underline'), style: { textDecoration: 'underline' } },
      { label: 'S', command: () => editor.chain().focus().toggleStrike().run(), active: editor.isActive('strike'), style: { textDecoration: 'line-through' } },
    ],
    [
      { label: 'H1', command: () => editor.chain().focus().toggleHeading({ level: 1 }).run(), active: editor.isActive('heading', { level: 1 }) },
      { label: 'H2', command: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), active: editor.isActive('heading', { level: 2 }) },
      { label: 'H3', command: () => editor.chain().focus().toggleHeading({ level: 3 }).run(), active: editor.isActive('heading', { level: 3 }) },
    ],
    [
      { label: '•', command: () => editor.chain().focus().toggleBulletList().run(), active: editor.isActive('bulletList') },
      { label: '1.', command: () => editor.chain().focus().toggleOrderedList().run(), active: editor.isActive('orderedList') },
      { label: '❝', command: () => editor.chain().focus().toggleBlockquote().run(), active: editor.isActive('blockquote') },
      { label: '⟨⟩', command: () => editor.chain().focus().toggleCodeBlock().run(), active: editor.isActive('codeBlock') },
    ],
    [
      { label: '↩', command: () => editor.chain().focus().undo().run(), active: false },
      { label: '↪', command: () => editor.chain().focus().redo().run(), active: false },
    ],
  ];

  return (
    <div className="editor-toolbar">
      {groups.map((group, gi) => (
        <div key={gi} style={{ display: 'contents' }}>
          {gi > 0 && <div className="toolbar-divider" />}
          <div className="toolbar-group">
            {group.map((btn, bi) => (
              <button
                key={bi}
                className={`toolbar-btn ${btn.active ? 'active' : ''}`}
                onClick={btn.command}
                style={btn.style || {}}
                title={btn.label}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
