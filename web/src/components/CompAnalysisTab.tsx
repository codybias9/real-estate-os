/**
 * CompAnalysisTab - Comparative Market Analysis with Negotiation Leverage
 *
 * Wave 3.1 Part 2 - Displays Comp-Critic adversarial analysis
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  DollarSign,
  BarChart3,
  Lightbulb,
  Home,
} from 'lucide-react';
import { apiClient } from '@/services/api';
import { formatCurrency } from '@/utils/format';

interface CompAnalysisTabProps {
  propertyId: string;
  property: any;
}

export function CompAnalysisTab({ propertyId, property }: CompAnalysisTabProps) {
  // Fetch comp analysis
  const {
    data: analysis,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['comp-analysis', propertyId],
    queryFn: () => apiClient.getCompAnalysis(propertyId),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <BarChart3 className="mx-auto h-12 w-12 animate-pulse text-primary-500" />
          <p className="mt-4 text-sm text-gray-500">Analyzing comparable properties...</p>
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
              <h3 className="text-sm font-medium text-red-800">Comp Analysis Failed</h3>
              <p className="mt-1 text-sm text-red-700">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis || analysis.error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-start">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Analysis Unavailable</h3>
              <p className="mt-1 text-sm text-yellow-700">
                {analysis?.error || 'No comparable properties found'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Comparative Market Analysis</h3>
        <p className="mt-1 text-sm text-gray-500">
          Adversarial comp analysis with negotiation leverage (powered by Comp-Critic)
        </p>
      </div>

      {/* Market Position Card */}
      <MarketPositionCard analysis={analysis} />

      {/* Negotiation Leverage Card */}
      <NegotiationLeverageCard analysis={analysis} />

      {/* Offer Range Card */}
      <OfferRangeCard analysis={analysis} />

      {/* Comparable Properties */}
      <ComparablePropertiesList comps={analysis.comps || []} />

      {/* Recommendations, Risks, Opportunities */}
      <InsightsGrid analysis={analysis} />
    </div>
  );
}

function MarketPositionCard({ analysis }: { analysis: any }) {
  const { market_position, price_deviation_percent, num_comps } = analysis;

  const getPositionConfig = (position: string) => {
    switch (position) {
      case 'overvalued':
        return {
          icon: TrendingUp,
          color: 'red',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          iconColor: 'text-red-600',
          label: 'Overvalued',
          description: 'Priced above market average',
        };
      case 'undervalued':
        return {
          icon: TrendingDown,
          color: 'green',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          iconColor: 'text-green-600',
          label: 'Undervalued',
          description: 'Priced below market average',
        };
      default:
        return {
          icon: Minus,
          color: 'blue',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          textColor: 'text-blue-800',
          iconColor: 'text-blue-600',
          label: 'Fairly Valued',
          description: 'Priced at market average',
        };
    }
  };

  const config = getPositionConfig(market_position);
  const Icon = config.icon;

  return (
    <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`rounded-full p-2 ${config.bgColor}`}>
            <Icon className={`h-6 w-6 ${config.iconColor}`} />
          </div>
          <div>
            <h4 className={`font-semibold ${config.textColor}`}>{config.label}</h4>
            <p className="text-sm text-gray-600">{config.description}</p>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${config.textColor}`}>
            {price_deviation_percent > 0 ? '+' : ''}
            {price_deviation_percent.toFixed(1)}%
          </div>
          <p className="text-xs text-gray-500">vs {num_comps} comps</p>
        </div>
      </div>
    </div>
  );
}

function NegotiationLeverageCard({ analysis }: { analysis: any }) {
  const { negotiation_leverage, negotiation_strategy } = analysis;

  const leveragePercent = Math.round(negotiation_leverage * 100);

  const getStrategyConfig = (strategy: string) => {
    switch (strategy) {
      case 'aggressive':
        return {
          color: 'green',
          label: 'Aggressive',
          description: 'Push hard for discount',
        };
      case 'cautious':
        return {
          color: 'yellow',
          label: 'Cautious',
          description: 'Limited negotiation room',
        };
      default:
        return {
          color: 'blue',
          label: 'Moderate',
          description: 'Balanced approach',
        };
    }
  };

  const strategyConfig = getStrategyConfig(negotiation_strategy);

  // Leverage gauge color
  const getLeverageColor = (leverage: number) => {
    if (leverage >= 0.7) return 'bg-green-500';
    if (leverage >= 0.4) return 'bg-blue-500';
    return 'bg-yellow-500';
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="font-semibold text-gray-900">Negotiation Leverage</h4>
          <p className="text-sm text-gray-500">Buyer's bargaining power</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{leveragePercent}%</div>
          <p className="text-xs text-gray-500">Leverage score</p>
        </div>
      </div>

      {/* Leverage Gauge */}
      <div className="mb-4">
        <div className="h-3 w-full bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${getLeverageColor(negotiation_leverage)} transition-all duration-500`}
            style={{ width: `${leveragePercent}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>Low</span>
          <span>Medium</span>
          <span>High</span>
        </div>
      </div>

      {/* Strategy Badge */}
      <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium bg-${strategyConfig.color}-100 text-${strategyConfig.color}-800`}>
        <Target className="h-4 w-4" />
        <span>{strategyConfig.label} Strategy</span>
      </div>
      <p className="mt-2 text-sm text-gray-600">{strategyConfig.description}</p>
    </div>
  );
}

function OfferRangeCard({ analysis }: { analysis: any }) {
  const { recommended_offer_range, subject_price } = analysis;

  if (!recommended_offer_range) return null;

  const minOffer = recommended_offer_range.min;
  const maxOffer = recommended_offer_range.max;
  const midOffer = (minOffer + maxOffer) / 2;

  const minDiscount = ((subject_price - maxOffer) / subject_price) * 100;
  const maxDiscount = ((subject_price - minOffer) / subject_price) * 100;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center gap-2 mb-3">
        <DollarSign className="h-5 w-5 text-primary-600" />
        <h4 className="font-semibold text-gray-900">Recommended Offer Range</h4>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Minimum</p>
          <p className="text-lg font-semibold text-gray-900">{formatCurrency(minOffer)}</p>
          <p className="text-xs text-green-600">{maxDiscount.toFixed(1)}% off</p>
        </div>
        <div className="text-center border-x border-gray-200">
          <p className="text-xs text-gray-500 mb-1">Target</p>
          <p className="text-lg font-semibold text-primary-600">{formatCurrency(midOffer)}</p>
          <p className="text-xs text-gray-500">{((minDiscount + maxDiscount) / 2).toFixed(1)}% off</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Maximum</p>
          <p className="text-lg font-semibold text-gray-900">{formatCurrency(maxOffer)}</p>
          <p className="text-xs text-green-600">{minDiscount.toFixed(1)}% off</p>
        </div>
      </div>

      <div className="pt-3 border-t border-gray-200 flex items-center justify-between text-sm">
        <span className="text-gray-600">Asking Price</span>
        <span className="font-medium text-gray-900">{formatCurrency(subject_price)}</span>
      </div>
    </div>
  );
}

function ComparablePropertiesList({ comps }: { comps: any[] }) {
  if (!comps || comps.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
        <Home className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-500">No comparable properties found</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="px-4 py-3 border-b border-gray-200">
        <h4 className="font-semibold text-gray-900">Comparable Properties</h4>
        <p className="text-sm text-gray-500">{comps.length} properties analyzed</p>
      </div>
      <div className="divide-y divide-gray-200">
        {comps.slice(0, 10).map((comp, index) => (
          <CompPropertyRow key={comp.property_id} comp={comp} rank={index + 1} />
        ))}
      </div>
    </div>
  );
}

function CompPropertyRow({ comp, rank }: { comp: any; rank: number }) {
  const similarityPercent = Math.round(comp.similarity_score * 100);

  return (
    <div className="px-4 py-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
            <span className="text-sm font-medium text-gray-600">#{rank}</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">
                {formatCurrency(comp.listing_price)}
              </span>
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                similarityPercent >= 90
                  ? 'bg-green-100 text-green-800'
                  : similarityPercent >= 75
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {similarityPercent}% match
              </span>
            </div>
            <p className="text-xs text-gray-500">{formatCurrency(comp.price_per_sqft)}/sqft</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function InsightsGrid({ analysis }: { analysis: any }) {
  const { recommendations, risk_factors, opportunities } = analysis;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Recommendations */}
      <InsightCard
        title="Recommendations"
        icon={CheckCircle}
        items={recommendations || []}
        color="blue"
      />

      {/* Risk Factors */}
      <InsightCard
        title="Risk Factors"
        icon={AlertTriangle}
        items={risk_factors || []}
        color="yellow"
      />

      {/* Opportunities */}
      <InsightCard
        title="Opportunities"
        icon={Lightbulb}
        items={opportunities || []}
        color="green"
      />
    </div>
  );
}

function InsightCard({
  title,
  icon: Icon,
  items,
  color,
}: {
  title: string;
  icon: React.ElementType;
  items: string[];
  color: 'blue' | 'yellow' | 'green';
}) {
  const colorConfig = {
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-600',
      text: 'text-blue-900',
    },
    yellow: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      icon: 'text-yellow-600',
      text: 'text-yellow-900',
    },
    green: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-600',
      text: 'text-green-900',
    },
  };

  const config = colorConfig[color];

  return (
    <div className={`rounded-lg border ${config.border} ${config.bg} p-4`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`h-5 w-5 ${config.icon}`} />
        <h4 className={`font-semibold ${config.text}`}>{title}</h4>
      </div>
      {items.length > 0 ? (
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="text-gray-400 mt-1">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-500 italic">None identified</p>
      )}
    </div>
  );
}
