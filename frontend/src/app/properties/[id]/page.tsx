'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { propertiesApi, enrichmentApi, scoringApi } from '@/lib/api';
import { Property, PropertyEnrichment, PropertyScore } from '@/types';

export default function PropertyDetailPage() {
  const params = useParams();
  const propertyId = parseInt(params.id as string);

  const [property, setProperty] = useState<Property | null>(null);
  const [enrichment, setEnrichment] = useState<PropertyEnrichment | null>(null);
  const [score, setScore] = useState<PropertyScore | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (propertyId) {
      loadPropertyData();
    }
  }, [propertyId]);

  const loadPropertyData = async () => {
    try {
      const propRes = await propertiesApi.get(propertyId);
      setProperty(propRes.data);

      // Try to load enrichment and score
      try {
        const enrichRes = await enrichmentApi.get(propertyId);
        setEnrichment(enrichRes.data);
      } catch (e) {
        console.log('No enrichment data');
      }

      try {
        const scoreRes = await scoringApi.get(propertyId);
        setScore(scoreRes.data);
      } catch (e) {
        console.log('No score data');
      }
    } catch (error) {
      console.error('Error loading property:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center py-12">Loading property...</div>
      </div>
    );
  }

  if (!property) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="card text-center py-12">
          <p className="text-gray-500">Property not found</p>
          <Link href="/properties" className="btn-primary mt-4 inline-block">
            Back to Properties
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6">
        <Link href="/properties" className="text-sm text-primary-600 hover:text-primary-700 mb-2 inline-block">
          ← Back to Properties
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">{property.address}</h1>
        <p className="text-lg text-gray-500">{property.city}, {property.state} {property.zip_code}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Price & Details */}
          <div className="card">
            <div className="flex items-start justify-between mb-6">
              <div>
                <p className="text-4xl font-bold text-gray-900">
                  ${property.price.toLocaleString()}
                </p>
                <p className="text-sm text-gray-500 mt-1">Listing Price</p>
              </div>
              <span className={`badge badge-${property.status === 'scored' ? 'success' : 'info'}`}>
                {property.status}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-2xl font-semibold text-gray-900">{property.bedrooms || '-'}</p>
                <p className="text-sm text-gray-500">Bedrooms</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-gray-900">{property.bathrooms || '-'}</p>
                <p className="text-sm text-gray-500">Bathrooms</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-gray-900">{property.sqft?.toLocaleString() || '-'}</p>
                <p className="text-sm text-gray-500">Sq Ft</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-gray-900">{property.year_built || '-'}</p>
                <p className="text-sm text-gray-500">Year Built</p>
              </div>
            </div>
          </div>

          {/* Description */}
          {property.description && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
              <p className="text-gray-700">{property.description}</p>
            </div>
          )}

          {/* Features */}
          {property.features && property.features.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Features</h2>
              <div className="flex flex-wrap gap-2">
                {property.features.map((feature, idx) => (
                  <span key={idx} className="badge-info">{feature}</span>
                ))}
              </div>
            </div>
          )}

          {/* Enrichment Data */}
          {enrichment && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Enrichment Data</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Tax Assessment</p>
                  <p className="text-base font-medium text-gray-900">
                    ${enrichment.tax_assessment_value?.toLocaleString() || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Annual Tax</p>
                  <p className="text-base font-medium text-gray-900">
                    ${enrichment.annual_tax_amount?.toLocaleString() || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">School Rating</p>
                  <p className="text-base font-medium text-gray-900">
                    {enrichment.school_rating || 'N/A'}/10
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Walk Score</p>
                  <p className="text-base font-medium text-gray-900">
                    {enrichment.walkability_score || 'N/A'}/100
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Crime Rate</p>
                  <p className="text-base font-medium text-gray-900">
                    {enrichment.crime_rate || 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Median Rent</p>
                  <p className="text-base font-medium text-gray-900">
                    ${enrichment.median_rent?.toLocaleString() || 'N/A'}/mo
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Investment Score */}
          {score && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Investment Score</h2>
              <div className="text-center mb-4">
                <div className={`text-6xl font-bold ${
                  score.total_score >= 80 ? 'text-green-600' :
                  score.total_score >= 60 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {score.total_score}
                </div>
                <div className="text-sm text-gray-500 mt-1">out of 100</div>
              </div>

              <div className="mb-4">
                <span className={`badge ${
                  score.recommendation === 'strong_buy' ? 'badge-success' :
                  score.recommendation === 'buy' ? 'badge-info' :
                  score.recommendation === 'hold' ? 'badge-warning' :
                  'badge-danger'
                } text-lg px-4 py-2`}>
                  {score.recommendation.replace('_', ' ').toUpperCase()}
                </span>
              </div>

              <p className="text-sm text-gray-700 mb-4">{score.recommendation_reason}</p>

              <div className="border-t pt-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Score Breakdown</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Price</span>
                    <span className="font-medium">{score.score_breakdown.price_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Investment</span>
                    <span className="font-medium">{score.score_breakdown.investment_metrics_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Location</span>
                    <span className="font-medium">{score.score_breakdown.location_quality_score}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Condition</span>
                    <span className="font-medium">{score.score_breakdown.property_condition_score}</span>
                  </div>
                </div>
              </div>

              <div className="border-t pt-4 mt-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Risk Level</h3>
                <span className={`badge ${
                  score.risk_level === 'low' ? 'badge-success' :
                  score.risk_level === 'medium' ? 'badge-warning' :
                  'badge-danger'
                }`}>
                  {score.risk_level.toUpperCase()}
                </span>
                {score.risk_factors.length > 0 && (
                  <ul className="mt-2 text-xs text-gray-600 space-y-1">
                    {score.risk_factors.map((factor, idx) => (
                      <li key={idx}>• {factor}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
            <div className="space-y-2">
              <button className="btn-primary w-full">Generate Investor Memo</button>
              <button className="btn-secondary w-full">Add to Campaign</button>
              <Link href={property.url || '#'} target="_blank" className="btn-secondary w-full block text-center">
                View Original Listing
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
