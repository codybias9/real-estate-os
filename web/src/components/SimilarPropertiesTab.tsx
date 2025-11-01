/**
 * SimilarPropertiesTab - Display ML-powered similar properties
 *
 * Wave 2.4 - Uses Qdrant vector database for similarity search
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Home,
  TrendingUp,
  MapPin,
  DollarSign,
  Bed,
  Bath,
  Sparkles,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { apiClient } from '@/services/api';
import type { SimilarProperty } from '@/types/provenance';
import { formatCurrency } from '@/utils/format';

interface SimilarPropertiesTabProps {
  propertyId: string;
  property: any; // PropertyDetail type
}

export function SimilarPropertiesTab({ propertyId, property }: SimilarPropertiesTabProps) {
  const [topK, setTopK] = useState(10);
  const [propertyTypeFilter, setPropertyTypeFilter] = useState<string | undefined>(undefined);
  const [userId] = useState(1); // TODO: Get from auth context
  const [feedback, setFeedback] = useState<Record<string, 'like' | 'dislike'>>({});

  // Fetch similar properties
  const {
    data: similarData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['similar-properties', propertyId, topK, propertyTypeFilter],
    queryFn: () =>
      apiClient.getSimilarProperties(propertyId, {
        top_k: topK,
        property_type: propertyTypeFilter,
      }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handleFeedback = async (targetPropertyId: string, feedbackType: 'like' | 'dislike') => {
    try {
      await apiClient.submitFeedback(targetPropertyId, userId, feedbackType);
      setFeedback((prev) => ({ ...prev, [targetPropertyId]: feedbackType }));
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <Sparkles className="mx-auto h-12 w-12 animate-pulse text-primary-500" />
          <p className="mt-4 text-sm text-gray-500">Finding similar properties...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error Loading Similar Properties</h3>
              <p className="mt-1 text-sm text-red-700">
                {error instanceof Error ? error.message : 'An unknown error occurred'}
              </p>
              <button
                onClick={() => refetch()}
                className="mt-3 rounded-md bg-red-100 px-3 py-1 text-sm font-medium text-red-800 hover:bg-red-200"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const similarProperties = similarData?.similar_properties || [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Similar Properties</h3>
          <p className="mt-1 text-sm text-gray-500">
            ML-powered recommendations based on property characteristics
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Top K Selector */}
          <select
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={50}>Top 50</option>
          </select>

          {/* Property Type Filter */}
          <select
            value={propertyTypeFilter || ''}
            onChange={(e) => setPropertyTypeFilter(e.target.value || undefined)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">All Types</option>
            <option value="Single Family">Single Family</option>
            <option value="Condo">Condo</option>
            <option value="Townhouse">Townhouse</option>
            <option value="Multi-Family">Multi-Family</option>
            <option value="Land">Land</option>
          </select>
        </div>
      </div>

      {/* Error Message (if service unavailable) */}
      {similarData?.error && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Service Unavailable</h3>
              <p className="mt-1 text-sm text-yellow-700">{similarData.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results Count */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary-500" />
            <span className="text-sm font-medium text-gray-900">
              Found {similarProperties.length} similar {similarProperties.length === 1 ? 'property' : 'properties'}
            </span>
          </div>
          <div className="text-xs text-gray-500">
            Powered by Portfolio Twin ML model
          </div>
        </div>
      </div>

      {/* Similar Properties List */}
      {similarProperties.length === 0 ? (
        <div className="text-center py-12">
          <Home className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-sm text-gray-500">No similar properties found</p>
          <p className="mt-1 text-xs text-gray-400">
            Try adjusting the filters or check back later
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {similarProperties.map((similar: SimilarProperty) => (
            <SimilarPropertyCard
              key={similar.property_id}
              property={similar}
              feedback={feedback[similar.property_id]}
              onFeedback={(type) => handleFeedback(similar.property_id, type)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface SimilarPropertyCardProps {
  property: SimilarProperty;
  feedback?: 'like' | 'dislike';
  onFeedback: (type: 'like' | 'dislike') => void;
}

function SimilarPropertyCard({ property, feedback, onFeedback }: SimilarPropertyCardProps) {
  const similarityPercent = Math.round(property.similarity_score * 100);

  // Determine similarity badge color
  const getBadgeColor = (score: number) => {
    if (score >= 0.9) return 'bg-green-100 text-green-800 border-green-200';
    if (score >= 0.75) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 hover:border-primary-300 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between">
        {/* Property Info */}
        <div className="flex-1 space-y-2">
          {/* Similarity Score Badge */}
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getBadgeColor(property.similarity_score)}`}>
              <TrendingUp className="h-3 w-3" />
              {similarityPercent}% Match
            </span>
            {property.confidence && (
              <span className="text-xs text-gray-500">
                Confidence: {Math.round(property.confidence * 100)}%
              </span>
            )}
          </div>

          {/* Property Details */}
          <div className="grid grid-cols-2 gap-3">
            {/* Price */}
            {property.listing_price && (
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-900">
                  {formatCurrency(property.listing_price)}
                </span>
              </div>
            )}

            {/* Beds/Baths */}
            <div className="flex items-center gap-3">
              {property.bedrooms && (
                <div className="flex items-center gap-1">
                  <Bed className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">{property.bedrooms} bed</span>
                </div>
              )}
              {property.bathrooms && (
                <div className="flex items-center gap-1">
                  <Bath className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">{property.bathrooms} bath</span>
                </div>
              )}
            </div>

            {/* Property Type */}
            {property.property_type && (
              <div className="flex items-center gap-2">
                <Home className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-700">{property.property_type}</span>
              </div>
            )}

            {/* Location */}
            {property.zipcode && (
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-700">{property.zipcode}</span>
              </div>
            )}
          </div>
        </div>

        {/* Feedback Buttons */}
        <div className="ml-4 flex flex-col gap-2">
          <button
            onClick={() => onFeedback('like')}
            className={`rounded-md p-2 transition-colors ${
              feedback === 'like'
                ? 'bg-green-100 text-green-700'
                : 'text-gray-400 hover:bg-gray-100 hover:text-green-600'
            }`}
            title="Like this match"
          >
            <ThumbsUp className="h-4 w-4" />
          </button>
          <button
            onClick={() => onFeedback('dislike')}
            className={`rounded-md p-2 transition-colors ${
              feedback === 'dislike'
                ? 'bg-red-100 text-red-700'
                : 'text-gray-400 hover:bg-gray-100 hover:text-red-600'
            }`}
            title="Dislike this match"
          >
            <ThumbsDown className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* View Property Link */}
      <div className="mt-3 border-t border-gray-100 pt-3">
        <button className="text-xs font-medium text-primary-600 hover:text-primary-700">
          View Property Details →
        </button>
      </div>
    </div>
  );
}
