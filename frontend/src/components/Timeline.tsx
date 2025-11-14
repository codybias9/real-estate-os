'use client';

/**
 * Timeline component with real-time SSE updates
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useTimeline, useTimelineSubscription, useAddComment, useAddNote } from '@/hooks';
import { LoadingSpinner } from './LoadingSpinner';
import { formatRelativeDate, getInitials } from '@/lib/utils';
import { EventType, type TimelineEvent } from '@/types';
import toast from 'react-hot-toast';

interface TimelineProps {
  propertyId: string;
}

export function Timeline({ propertyId }: TimelineProps) {
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');

  const { data: events, isLoading } = useTimeline(propertyId);
  const { connected, error } = useTimelineSubscription(propertyId);
  const addComment = useAddComment();
  const addNote = useAddNote();

  const handleAddComment = async () => {
    if (!commentText.trim()) return;

    try {
      await addComment.mutateAsync({
        property_id: propertyId,
        content: commentText,
      });
      setCommentText('');
      setShowCommentForm(false);
      toast.success('Comment added');
    } catch (error) {
      toast.error('Failed to add comment');
      console.error(error);
    }
  };

  const handleAddNote = async () => {
    if (!noteTitle.trim() || !noteContent.trim()) return;

    try {
      await addNote.mutateAsync({
        property_id: propertyId,
        title: noteTitle,
        content: noteContent,
      });
      setNoteTitle('');
      setNoteContent('');
      setShowNoteForm(false);
      toast.success('Note added');
    } catch (error) {
      toast.error('Failed to add note');
      console.error(error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* SSE Connection Status */}
      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-sm text-yellow-800">
            Real-time updates unavailable. Refresh to see latest changes.
          </p>
        </div>
      )}

      {connected && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center space-x-2">
          <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
          <p className="text-sm text-green-800">Live updates enabled</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex space-x-3">
        <button
          onClick={() => setShowCommentForm(!showCommentForm)}
          className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Add Comment
        </button>
        <button
          onClick={() => setShowNoteForm(!showNoteForm)}
          className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Add Note
        </button>
      </div>

      {/* Comment Form */}
      {showCommentForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <textarea
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Write a comment..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <div className="mt-3 flex justify-end space-x-2">
            <button
              onClick={() => setShowCommentForm(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              onClick={handleAddComment}
              disabled={!commentText.trim() || addComment.isPending}
              className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {addComment.isPending ? 'Adding...' : 'Add Comment'}
            </button>
          </div>
        </div>
      )}

      {/* Note Form */}
      {showNoteForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
          <input
            type="text"
            value={noteTitle}
            onChange={(e) => setNoteTitle(e.target.value)}
            placeholder="Note title..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <textarea
            value={noteContent}
            onChange={(e) => setNoteContent(e.target.value)}
            placeholder="Write note content (supports Markdown)..."
            rows={5}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <div className="flex justify-end space-x-2">
            <button
              onClick={() => setShowNoteForm(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              onClick={handleAddNote}
              disabled={!noteTitle.trim() || !noteContent.trim() || addNote.isPending}
              className="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {addNote.isPending ? 'Adding...' : 'Add Note'}
            </button>
          </div>
        </div>
      )}

      {/* Timeline Events */}
      {!events || events.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="mt-4">No timeline events yet</p>
          <p className="text-sm mt-2">Add a comment or note to get started</p>
        </div>
      ) : (
        <div className="flow-root">
          <ul className="-mb-8">
            {events.map((event, eventIdx) => (
              <li key={event.id}>
                <div className="relative pb-8">
                  {eventIdx !== events.length - 1 && (
                    <span
                      className="absolute left-5 top-5 -ml-px h-full w-0.5 bg-gray-200"
                      aria-hidden="true"
                    />
                  )}
                  <TimelineEventItem event={event} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function TimelineEventItem({ event }: { event: TimelineEvent }) {
  const isSystemEvent = event.is_system_event;
  const userName = event.user_name || 'System';

  const iconBgColor = isSystemEvent ? 'bg-gray-100' : 'bg-primary-100';
  const iconColor = isSystemEvent ? 'text-gray-600' : 'text-primary-600';

  return (
    <div className="relative flex items-start space-x-3">
      <div className="relative">
        <div
          className={`h-10 w-10 rounded-full ${iconBgColor} flex items-center justify-center ring-4 ring-white`}
        >
          {isSystemEvent ? (
            <svg className={`h-5 w-5 ${iconColor}`} fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <span className={`text-sm font-medium ${iconColor}`}>{getInitials(userName)}</span>
          )}
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <div>
          <div className="text-sm">
            <span className="font-medium text-gray-900">{event.title}</span>
          </div>
          <p className="mt-0.5 text-xs text-gray-500">{formatRelativeDate(event.created_at)}</p>
        </div>

        {event.content_html ? (
          <div className="mt-2 text-sm text-gray-700 prose prose-sm max-w-none">
            <div dangerouslySetInnerHTML={{ __html: event.content_html }} />
          </div>
        ) : (
          event.content && (
            <div className="mt-2 text-sm text-gray-700 prose prose-sm max-w-none">
              <ReactMarkdown>{event.content}</ReactMarkdown>
            </div>
          )
        )}

        {event.tags && event.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {event.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {event.attachments && event.attachments.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-gray-500">{event.attachments.length} attachment(s)</p>
          </div>
        )}
      </div>
    </div>
  );
}
