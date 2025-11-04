import React from 'react';
import { MessageSquare, Plus, Trash2, Clock } from 'lucide-react';

const ChatSidebar = ({ 
  conversations, 
  currentConversationId, 
  onSelectConversation, 
  onNewConversation,
  onDeleteConversation 
}) => {
  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium shadow-lg hover:shadow-xl"
        >
          <Plus size={20} />
          New Chat
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {conversations.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <MessageSquare size={48} className="mx-auto mb-3 opacity-50" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1">Start a new chat!</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`
                group relative p-3 rounded-lg cursor-pointer transition-all
                ${currentConversationId === conv.id 
                  ? 'bg-gray-800 border border-blue-500 shadow-lg' 
                  : 'bg-gray-800/50 hover:bg-gray-800 border border-transparent hover:border-gray-700'
                }
              `}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <MessageSquare size={16} className="text-blue-400 flex-shrink-0" />
                    <h3 className="text-sm font-medium text-white truncate">
                      {conv.title || 'New Conversation'}
                    </h3>
                  </div>
                  
                  {conv.lastMessage && (
                    <p className="text-xs text-gray-400 truncate mb-2">
                      {conv.lastMessage}
                    </p>
                  )}
                  
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock size={12} />
                    {new Date(conv.updated_at).toLocaleDateString()}
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                  title="Delete conversation"
                >
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>

              {conv.message_count > 0 && (
                <div className="absolute top-2 right-2 bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full font-medium">
                  {conv.message_count}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-500 text-center">
          {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
};

export default ChatSidebar;
