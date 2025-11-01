/**
 * TimelineTab - Display property timeline/activity feed
 * Placeholder for future timeline functionality
 */

import React from 'react';
import { Clock, FileText, Mail, Phone, DollarSign } from 'lucide-react';

interface TimelineTabProps {
  propertyId: string;
}

interface TimelineEvent {
  id: string;
  type: 'document' | 'email' | 'call' | 'deal';
  title: string;
  description: string;
  timestamp: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

export function TimelineTab({ propertyId }: TimelineTabProps) {
  // Placeholder data - in production, this would fetch from API
  const events: TimelineEvent[] = [
    {
      id: '1',
      type: 'document',
      title: 'Investment memo generated',
      description: 'Property analysis document created for review',
      timestamp: '2025-11-01T10:30:00Z',
      icon: FileText,
      color: 'bg-blue-100 text-blue-600',
    },
    {
      id: '2',
      type: 'email',
      title: 'Outreach email sent',
      description: 'Initial contact email sent to owner',
      timestamp: '2025-11-01T09:15:00Z',
      icon: Mail,
      color: 'bg-green-100 text-green-600',
    },
    {
      id: '3',
      type: 'deal',
      title: 'Deal created',
      description: 'New deal pipeline entry created',
      timestamp: '2025-11-01T08:00:00Z',
      icon: DollarSign,
      color: 'bg-purple-100 text-purple-600',
    },
  ];

  return (
    <div className="p-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900">Activity Timeline</h3>
        </div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />

          {/* Events */}
          <div className="space-y-6">
            {events.map((event, idx) => (
              <div key={event.id} className="relative pl-14">
                {/* Timeline dot */}
                <div className={`absolute left-4 top-2 rounded-full p-2 ${event.color}`}>
                  <event.icon className="h-4 w-4" />
                </div>

                {/* Event card */}
                <div className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-gray-900">{event.title}</h4>
                      <p className="mt-1 text-sm text-gray-600">{event.description}</p>
                      <p className="mt-2 text-xs text-gray-500">
                        {new Date(event.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Placeholder message */}
        <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
          <Clock className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-sm text-gray-600">
            Timeline functionality coming soon
          </p>
          <p className="mt-2 text-xs text-gray-500">
            This will show property activity, communications, and deal progression
          </p>
        </div>
      </div>
    </div>
  );
}
