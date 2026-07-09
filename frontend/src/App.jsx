import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Bot, 
  User, 
  Sparkles, 
  Loader2, 
  Plus, 
  ChevronDown, 
  PanelLeftClose, 
  PanelLeftOpen, 
  SquarePen, 
  MessageSquare, 
  Trash2, 
  RefreshCw, 
  Database,
  ArrowUp,
  FileSpreadsheet,
  Calendar,
  Mail
} from 'lucide-react';

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am Jarvis, your enterprise intelligence agent. I can help you search emails, check calendar events, and analyze Excel files or JSR trackers. What can I do for you today?' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [selectedModel, setSelectedModel] = useState('Jarvis (Mistral-Large)');
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [isReloading, setIsReloading] = useState(false);
  const [reloadMessage, setReloadMessage] = useState('');
  
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Adjust height of textarea dynamically based on input length
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const newMessages = [...messages, { role: 'user', content: userMessage }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      // Pass the previous messages as history, excluding the greeting
      const history = newMessages.slice(1, -1).map(msg => ({ role: msg.role, content: msg.content }));
      
      const response = await axios.post('http://localhost:8000/chat', {
        message: userMessage,
        history: history
      });

      setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
    } catch (error) {
      console.error('Error fetching response:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please make sure the backend server is running and try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleNewChat = () => {
    setMessages([
      { role: 'assistant', content: 'Hello! I am Jarvis, your enterprise intelligence agent. I can help you search emails, check calendar events, and analyze Excel files or JSR trackers. What can I do for you today?' }
    ]);
    setInput('');
  };

  const handleReloadData = async () => {
    setIsReloading(true);
    setReloadMessage('');
    try {
      const response = await axios.post('http://localhost:8000/reload');
      setReloadMessage('Data reloaded successfully! ✅');
      setTimeout(() => setReloadMessage(''), 3000);
    } catch (error) {
      console.error('Error reloading data:', error);
      setReloadMessage('Failed to reload data ❌');
      setTimeout(() => setReloadMessage(''), 4000);
    } finally {
      setIsReloading(false);
    }
  };

  const quickPrompts = [
    { label: 'Summarize pod4jsr JSR file', text: 'Summarize the tables and projects in the pod4jsr sheet.', icon: FileSpreadsheet, color: 'text-emerald-400' },
    { label: "Check today's schedule", text: "What meetings or events do I have scheduled for today?", icon: Calendar, color: 'text-indigo-400' },
    { label: 'Search recent emails', text: 'Show me my recent emails. Who are they from?', icon: Mail, color: 'text-amber-400' },
    { label: 'Check Panasonic SOW', text: 'What deliverables are defined in the Panasonic Scope of Work (SOW)?', icon: Sparkles, color: 'text-cyan-400' },
  ];

  const recentChats = [
    { title: 'Excel JSR Data Analysis', prompt: 'Summarize the tables and projects in the pod4jsr sheet.' },
    { title: "Today's Client Meetings", prompt: "What meetings or events do I have scheduled for today?" },
    { title: 'Email Updates & Actions', prompt: 'Show me my recent emails. Who are they from?' },
    { title: 'Panasonic SOW Scope', prompt: 'What deliverables are defined in the Panasonic Scope of Work (SOW)?' },
  ];

  // Markdown Custom Renderers for beautiful ChatGPT style elements
  const markdownRenderers = {
    table: ({ node, ...props }) => (
      <div className="overflow-x-auto my-4 rounded-lg border border-slate-700">
        <table className="min-w-full divide-y divide-slate-700 bg-[#2d2d2d]" {...props} />
      </div>
    ),
    thead: ({ node, ...props }) => <thead className="bg-[#1e1e1e]" {...props} />,
    tbody: ({ node, ...props }) => <tbody className="divide-y divide-slate-700" {...props} />,
    tr: ({ node, ...props }) => <tr className="hover:bg-[#333333] transition-colors" {...props} />,
    th: ({ node, ...props }) => (
      <th className="px-4 py-2 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider border-r border-slate-700 last:border-r-0" {...props} />
    ),
    td: ({ node, ...props }) => (
      <td className="px-4 py-2 text-sm text-slate-200 border-r border-slate-700 last:border-r-0 whitespace-pre-wrap" {...props} />
    ),
    ul: ({ node, ...props }) => <ul className="list-disc pl-6 my-2 space-y-1 text-slate-200" {...props} />,
    ol: ({ node, ...props }) => <ol className="list-decimal pl-6 my-2 space-y-1 text-slate-200" {...props} />,
    li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
    h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mt-6 mb-3 text-slate-100 border-b border-slate-800 pb-1" {...props} />,
    h2: ({ node, ...props }) => <h2 className="text-xl font-bold mt-5 mb-2 text-slate-100" {...props} />,
    h3: ({ node, ...props }) => <h3 className="text-lg font-semibold mt-4 mb-2 text-slate-200" {...props} />,
    p: ({ node, ...props }) => <p className="my-2 leading-relaxed text-slate-300 break-words" {...props} />,
    a: ({ node, ...props }) => <a className="text-cyan-400 hover:underline font-medium" target="_blank" rel="noopener noreferrer" {...props} />,
    code: ({ node, inline, className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || '');
      return !inline ? (
        <div className="relative my-4">
          <div className="bg-[#1e1e1e] text-xs text-slate-400 px-4 py-1.5 rounded-t-lg border-b border-slate-800 flex justify-between items-center font-sans">
            <span>{match ? match[1] : 'code'}</span>
          </div>
          <pre className="overflow-x-auto bg-[#0d0d0d] p-4 rounded-b-lg border border-t-0 border-slate-800 font-mono text-sm text-cyan-300">
            <code {...props}>{children}</code>
          </pre>
        </div>
      ) : (
        <code className="bg-[#2d2d2d] px-1.5 py-0.5 rounded text-sm text-rose-400 font-mono" {...props}>
          {children}
        </code>
      );
    },
    blockquote: ({ node, ...props }) => (
      <blockquote className="border-l-4 border-slate-500 pl-4 my-2 italic text-slate-400 bg-[#2d2d2d]/30 py-1 pr-2 rounded-r" {...props} />
    ),
  };

  return (
    <div className="flex h-screen bg-[#212121] text-[#ececec] font-sans overflow-hidden">
      
      {/* Sidebar - ChatGPT Style */}
      <div 
        className={`bg-[#171717] flex flex-col h-full border-r border-[#2d2d2d] transition-all duration-300 ease-in-out z-20
          ${isSidebarOpen ? 'w-64' : 'w-0 overflow-hidden border-r-0'}`}
      >
        {/* New Chat Button */}
        <div className="p-3.5 flex items-center justify-between gap-2">
          <button 
            onClick={handleNewChat}
            className="flex-1 flex items-center justify-between px-3 py-2.5 rounded-lg border border-[#4d4d4d] hover:bg-[#2d2d2d] text-sm text-white font-medium transition-all group"
          >
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
              New Chat
            </span>
            <SquarePen className="w-4 h-4 text-slate-400" />
          </button>
          
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="p-2.5 rounded-lg hover:bg-[#2d2d2d] text-slate-400 hover:text-white transition-colors"
            title="Close sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* Recent Chats / Quick Nav */}
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 select-none">
          <div className="text-[11px] font-semibold text-slate-500 px-3 py-1.5 uppercase tracking-wider">
            Quick Queries
          </div>
          {recentChats.map((chat, idx) => (
            <button
              key={idx}
              onClick={() => setInput(chat.prompt)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-left text-slate-300 hover:bg-[#2d2d2d] hover:text-white transition-colors group truncate"
            >
              <MessageSquare className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 flex-shrink-0" />
              <span className="truncate">{chat.title}</span>
            </button>
          ))}
        </div>

        {/* Sidebar Footer Operations */}
        <div className="p-3 border-t border-[#2d2d2d] space-y-2">
          {reloadMessage && (
            <div className="text-xs text-center font-medium bg-[#2d2d2d] py-1.5 px-3 rounded-lg border border-slate-700 animate-fade-in text-slate-200">
              {reloadMessage}
            </div>
          )}

          <button 
            onClick={handleReloadData}
            disabled={isReloading}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[#2d2d2d] hover:bg-[#3d3d3d] text-xs text-white font-medium border border-slate-700 transition-colors disabled:opacity-50"
          >
            {isReloading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
            ) : (
              <Database className="w-3.5 h-3.5 text-cyan-400" />
            )}
            {isReloading ? 'Reloading Data...' : 'Reload Excel Data'}
          </button>

          <button 
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-[#2d2d2d] text-xs text-slate-400 hover:text-white transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear Conversation
          </button>

          {/* User Profile Info */}
          <div className="flex items-center gap-2.5 px-2 py-2 mt-2">
            <div className="w-8 h-8 rounded-full bg-cyan-600 flex items-center justify-center text-white text-xs font-semibold shadow-inner">
              JA
            </div>
            <div className="flex-1 truncate">
              <p className="text-xs font-medium text-white truncate">Jarvis User</p>
              <p className="text-[10px] text-slate-500 truncate">Enterprise Intelligence</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-[#212121]">
        
        {/* Floating Sidebar Toggle (Only visible if sidebar is closed) */}
        {!isSidebarOpen && (
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="absolute top-3 left-3 p-2 rounded-lg bg-[#171717] hover:bg-[#2d2d2d] text-slate-400 hover:text-white border border-[#2d2d2d] transition-all z-10 shadow-md"
            title="Open sidebar"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        )}

        {/* Model Selection Header */}
        <header className="h-14 flex items-center justify-between px-4 border-b border-[#2d2d2d] bg-[#212121] sticky top-0 z-10">
          <div className="flex items-center gap-2 pl-12 md:pl-0">
            <div className="relative">
              <button 
                onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-slate-300 font-semibold hover:bg-[#2d2d2d] transition-all"
              >
                <span>{selectedModel}</span>
                <ChevronDown className="w-4 h-4 text-slate-500" />
              </button>
              
              {isModelDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-64 bg-[#171717] border border-[#2d2d2d] rounded-lg shadow-xl py-1 z-30">
                  <button 
                    onClick={() => { setSelectedModel('Jarvis (Mistral-Large)'); setIsModelDropdownOpen(false); }}
                    className="w-full px-4 py-2 text-xs text-left text-white hover:bg-[#2d2d2d] flex flex-col gap-0.5"
                  >
                    <span className="font-semibold">Jarvis (Mistral-Large)</span>
                    <span className="text-[10px] text-slate-500">Premium reasoning and deep Excel analysis</span>
                  </button>
                  <button 
                    onClick={() => { setSelectedModel('Jarvis (Mistral-Small)'); setIsModelDropdownOpen(false); }}
                    className="w-full px-4 py-2 text-xs text-left text-white hover:bg-[#2d2d2d] flex flex-col gap-0.5 border-t border-[#2d2d2d]"
                  >
                    <span className="font-semibold">Jarvis (Mistral-Small)</span>
                    <span className="text-[10px] text-slate-500">Ultra-fast general responses</span>
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-slate-400 font-medium">Backend Connected</span>
          </div>
        </header>

        {/* Message Container / Main chat view */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-0">
          
          {messages.length === 1 ? (
            /* Welcome / Empty state dashboard */
            <div className="max-w-2xl mx-auto h-full flex flex-col justify-center items-center pb-12 select-none">
              <div className="w-12 h-12 rounded-full bg-[#171717] border border-[#2d2d2d] flex items-center justify-center shadow-lg mb-6">
                <Bot className="w-7 h-7 text-cyan-400" />
              </div>
              <h2 className="text-2xl font-semibold text-white mb-8 text-center">
                What can I help with?
              </h2>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                {quickPrompts.map((prompt, idx) => {
                  const PromptIcon = prompt.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => setInput(prompt.text)}
                      className="flex flex-col items-start gap-1.5 p-4 rounded-xl border border-[#2d2d2d] hover:bg-[#2d2d2d] transition-all text-left group hover:border-[#4d4d4d]"
                    >
                      <PromptIcon className={`w-4 h-4 ${prompt.color} mb-1`} />
                      <span className="text-xs font-semibold text-slate-200">{prompt.label}</span>
                      <span className="text-[11px] text-slate-500 line-clamp-1">{prompt.text}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Standard chat history message stream */
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg, index) => (
                <div 
                  key={index} 
                  className={`flex gap-4 py-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {/* Bot Avatar */}
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-[#171717] border border-[#2d2d2d] flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                      <Bot className="w-4.5 h-4.5 text-cyan-400" />
                    </div>
                  )}

                  {/* Message Bubble/Text */}
                  {msg.role === 'user' ? (
                    <div className="max-w-[75%] bg-[#2f2f2f] text-slate-100 rounded-[22px] px-5 py-2.5 text-sm shadow-sm break-words leading-relaxed">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="flex-1 max-w-[90%] text-sm text-slate-200 overflow-hidden leading-relaxed pr-8">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]} 
                        components={markdownRenderers}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* User Avatar */}
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-[#2f2f2f] border border-slate-700 flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                      <User className="w-4 h-4 text-slate-300" />
                    </div>
                  )}
                </div>
              ))}

              {/* Bot thinking bubble indicator */}
              {isLoading && (
                <div className="flex gap-4 py-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-[#171717] border border-[#2d2d2d] flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                    <Bot className="w-4.5 h-4.5 text-cyan-400" />
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-400 text-sm py-2 px-1">
                    <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                    <span>Jarvis is thinking...</span>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar Section */}
        <footer className="w-full max-w-3xl mx-auto px-4 pb-6 pt-2 bg-[#212121]">
          <form onSubmit={handleSubmit} className="relative bg-[#2f2f2f] rounded-[24px] border border-[#3e3e3e] shadow-lg flex flex-col p-1.5 focus-within:border-slate-500 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Jarvis..."
              disabled={isLoading}
              rows={1}
              className="w-full bg-transparent border-0 outline-none text-[#ececec] placeholder-slate-500 px-4 py-2.5 text-sm resize-none focus:ring-0 max-h-[200px] overflow-y-auto"
            />
            
            <div className="flex items-center justify-between px-3 pb-1 pt-1.5 border-t border-[#3e3e3e]/30">
              <span className="text-[10px] text-slate-500 font-medium">
                Hold Shift + Enter for new line
              </span>
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="w-8 h-8 rounded-full bg-white text-black hover:bg-slate-200 transition-all flex items-center justify-center disabled:bg-[#3f3f3f] disabled:text-slate-500"
                title="Send message"
              >
                <ArrowUp className="w-4 h-4 stroke-[3]" />
              </button>
            </div>
          </form>
          <p className="text-center text-[10px] text-slate-500 mt-2 font-medium">
            Jarvis can make mistakes. Please verify important information.
          </p>
        </footer>

      </div>
    </div>
  );
}

export default App;
