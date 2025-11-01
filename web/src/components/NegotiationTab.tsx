/**
 * NegotiationTab - Strategic Negotiation Recommendation Interface
 *
 * Wave 3.2 - Displays Negotiation Brain strategic recommendations
 *
 * Features:
 * - Negotiation strategy recommendation (aggressive/moderate/cautious)
 * - Offer range calculator with buyer budget input
 * - Talking points and leverage indicators
 * - Deal structure recommendations
 * - Market condition and seller motivation indicators
 */

import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Target,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  DollarSign,
  MessageSquare,
  FileText,
  Clock,
  Shield,
  Zap,
  Lightbulb,
  Brain,
} from 'lucide-react';
import { apiClient } from '@/services/api';
import { formatCurrency } from '@/utils/format';

interface NegotiationTabProps {
  propertyId: string;
  property: any;
}

export function NegotiationTab({ propertyId, property }: NegotiationTabProps) {
  // Buyer constraints state
  const [maxBudget, setMaxBudget] = useState<number>(
    property.fields?.listing_price ? property.fields.listing_price * 1.1 : 500000
  );
  const [preferredBudget, setPreferredBudget] = useState<number>(
    property.fields?.listing_price || 450000
  );
  const [financingType, setFinancingType] = useState<string>('conventional');
  const [downPaymentPercent, setDownPaymentPercent] = useState<number>(20);
  const [desiredClosingDays, setDesiredClosingDays] = useState<number>(45);
  const [flexibility, setFlexibility] = useState<string>('moderate');

  const [showInputs, setShowInputs] = useState(true);

  // Fetch negotiation strategy
  const {
    data: strategy,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: [
      'negotiation-strategy',
      propertyId,
      maxBudget,
      preferredBudget,
      financingType,
      downPaymentPercent,
      desiredClosingDays,
      flexibility,
    ],
    queryFn: () =>
      apiClient.getNegotiationStrategy(propertyId, {
        max_budget: maxBudget,
        preferred_budget: preferredBudget,
        financing_type: financingType,
        down_payment_percent: downPaymentPercent,
        desired_closing_days: desiredClosingDays,
        flexibility: flexibility,
      }),
    enabled: false, // Manual trigger
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handleGenerateStrategy = () => {
    setShowInputs(false);
    refetch();
  };

  if (showInputs || !strategy) {
    return (
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start gap-3">
          <Brain className="h-8 w-8 text-primary-600 mt-1" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Negotiation Brain</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get AI-powered negotiation strategy based on your budget and market analysis
            </p>
          </div>
        </div>

        {/* Budget Inputs */}
        <BudgetInputsCard
          maxBudget={maxBudget}
          setMaxBudget={setMaxBudget}
          preferredBudget={preferredBudget}
          setPreferredBudget={setPreferredBudget}
          financingType={financingType}
          setFinancingType={setFinancingType}
          downPaymentPercent={downPaymentPercent}
          setDownPaymentPercent={setDownPaymentPercent}
          desiredClosingDays={desiredClosingDays}
          setDesiredClosingDays={setDesiredClosingDays}
          flexibility={flexibility}
          setFlexibility={setFlexibility}
          listingPrice={property.fields?.listing_price || 0}
        />

        {/* Generate Button */}
        <div className="flex justify-center">
          <button
            onClick={handleGenerateStrategy}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:bg-gray-400"
          >
            {isLoading ? (
              <>
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Brain className="h-5 w-5" />
                <span>Generate Negotiation Strategy</span>
              </>
            )}
          </button>
        </div>

        {/* Previous strategy if exists */}
        {strategy && (
          <div className="text-center">
            <button
              onClick={() => setShowInputs(false)}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              View previous recommendation →
            </button>
          </div>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <Brain className="mx-auto h-12 w-12 animate-pulse text-primary-500" />
          <p className="mt-4 text-sm text-gray-500">Analyzing negotiation strategy...</p>
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
              <h3 className="text-sm font-medium text-red-800">Strategy Generation Failed</h3>
              <p className="mt-1 text-sm text-red-700">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (strategy?.error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-start">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Strategy Unavailable</h3>
              <p className="mt-1 text-sm text-yellow-700">{strategy.error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header with Edit Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-3">
          <Brain className="h-8 w-8 text-primary-600 mt-1" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Negotiation Strategy</h3>
            <p className="mt-1 text-sm text-gray-500">
              AI-powered recommendations based on market analysis and your budget
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowInputs(true)}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Edit Inputs
        </button>
      </div>

      {/* Strategy Card */}
      <StrategyCard strategy={strategy} />

      {/* Offer Range Card */}
      <OfferRangeCard strategy={strategy} />

      {/* Market Context Grid */}
      <MarketContextGrid strategy={strategy} />

      {/* Talking Points */}
      <TalkingPointsList talkingPoints={strategy.talking_points || []} />

      {/* Deal Structure */}
      <DealStructureCard dealStructure={strategy.deal_structure || {}} />

      {/* Counter-Offer Strategy */}
      <CounterOfferStrategyCard counterStrategy={strategy.counter_offer_strategy || {}} />

      {/* Risks and Opportunities */}
      <RisksOpportunitiesGrid strategy={strategy} />
    </div>
  );
}

function BudgetInputsCard({
  maxBudget,
  setMaxBudget,
  preferredBudget,
  setPreferredBudget,
  financingType,
  setFinancingType,
  downPaymentPercent,
  setDownPaymentPercent,
  desiredClosingDays,
  setDesiredClosingDays,
  flexibility,
  setFlexibility,
  listingPrice,
}: any) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h4 className="font-semibold text-gray-900 mb-4">Your Budget & Constraints</h4>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Max Budget */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Maximum Budget
          </label>
          <input
            type="number"
            value={maxBudget}
            onChange={(e) => setMaxBudget(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="mt-1 text-xs text-gray-500">Your absolute ceiling</p>
        </div>

        {/* Preferred Budget */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Preferred Budget
          </label>
          <input
            type="number"
            value={preferredBudget}
            onChange={(e) => setPreferredBudget(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="mt-1 text-xs text-gray-500">Your target price</p>
        </div>

        {/* Financing Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Financing Type
          </label>
          <select
            value={financingType}
            onChange={(e) => setFinancingType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="conventional">Conventional</option>
            <option value="fha">FHA</option>
            <option value="va">VA</option>
            <option value="cash">Cash</option>
          </select>
        </div>

        {/* Down Payment */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Down Payment (%)
          </label>
          <input
            type="number"
            value={downPaymentPercent}
            onChange={(e) => setDownPaymentPercent(Number(e.target.value))}
            min="0"
            max="100"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Closing Timeline */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Desired Closing (days)
          </label>
          <input
            type="number"
            value={desiredClosingDays}
            onChange={(e) => setDesiredClosingDays(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Flexibility */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Flexibility
          </label>
          <select
            value={flexibility}
            onChange={(e) => setFlexibility(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="flexible">Flexible</option>
            <option value="moderate">Moderate</option>
            <option value="inflexible">Inflexible</option>
          </select>
        </div>
      </div>

      {/* Comparison to Listing */}
      {listingPrice > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Listing Price:</span>
            <span className="font-medium text-gray-900">{formatCurrency(listingPrice)}</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-gray-600">Your Budget vs Listing:</span>
            <span
              className={`font-medium ${
                maxBudget >= listingPrice ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {maxBudget >= listingPrice ? '+' : ''}
              {formatCurrency(maxBudget - listingPrice)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function StrategyCard({ strategy }: { strategy: any }) {
  const getStrategyConfig = (strategyType: string) => {
    switch (strategyType) {
      case 'aggressive':
        return {
          icon: Zap,
          color: 'green',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          iconColor: 'text-green-600',
          label: 'Aggressive',
          description: 'Push hard for discounts with strong leverage',
        };
      case 'cautious':
        return {
          icon: Shield,
          color: 'yellow',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          textColor: 'text-yellow-800',
          iconColor: 'text-yellow-600',
          label: 'Cautious',
          description: 'Conservative approach to maximize acceptance',
        };
      case 'walk_away':
        return {
          icon: AlertTriangle,
          color: 'red',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          iconColor: 'text-red-600',
          label: 'Walk Away',
          description: 'Property not recommended',
        };
      default:
        return {
          icon: Target,
          color: 'blue',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          textColor: 'text-blue-800',
          iconColor: 'text-blue-600',
          label: 'Moderate',
          description: 'Balanced approach with fair value focus',
        };
    }
  };

  const config = getStrategyConfig(strategy.strategy);
  const Icon = config.icon;
  const confidencePercent = Math.round(strategy.strategy_confidence * 100);

  return (
    <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-6`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className={`rounded-full p-3 ${config.bgColor}`}>
            <Icon className={`h-8 w-8 ${config.iconColor}`} />
          </div>
          <div>
            <h4 className={`text-xl font-semibold ${config.textColor}`}>{config.label} Strategy</h4>
            <p className="mt-1 text-sm text-gray-600">{config.description}</p>
            <p className="mt-3 text-sm text-gray-700">{strategy.strategy_rationale}</p>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-bold ${config.textColor}`}>{confidencePercent}%</div>
          <p className="text-xs text-gray-500">Confidence</p>
        </div>
      </div>
    </div>
  );
}

function OfferRangeCard({ strategy }: { strategy: any }) {
  const { recommended_initial_offer, recommended_max_offer, walk_away_price } = strategy;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-2 mb-4">
        <DollarSign className="h-5 w-5 text-primary-600" />
        <h4 className="font-semibold text-gray-900">Recommended Offer Range</h4>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Initial Offer</p>
          <p className="text-xl font-semibold text-primary-600">
            {formatCurrency(recommended_initial_offer)}
          </p>
          <p className="text-xs text-gray-500 mt-1">Start here</p>
        </div>
        <div className="text-center border-x border-gray-200">
          <p className="text-xs text-gray-500 mb-1">Maximum Offer</p>
          <p className="text-xl font-semibold text-gray-900">
            {formatCurrency(recommended_max_offer)}
          </p>
          <p className="text-xs text-gray-500 mt-1">Go up to</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Walk Away</p>
          <p className="text-xl font-semibold text-red-600">{formatCurrency(walk_away_price)}</p>
          <p className="text-xs text-gray-500 mt-1">Absolute max</p>
        </div>
      </div>

      {/* Justification */}
      {strategy.offer_justification && (
        <div className="pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-700 whitespace-pre-line">{strategy.offer_justification}</p>
        </div>
      )}
    </div>
  );
}

function MarketContextGrid({ strategy }: { strategy: any }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Market Condition */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="h-5 w-5 text-gray-600" />
          <h4 className="font-semibold text-gray-900">Market Condition</h4>
        </div>
        <p className="text-lg font-medium text-gray-900">
          {strategy.market_condition.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
        </p>
      </div>

      {/* Seller Motivation */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-2">
          <Target className="h-5 w-5 text-gray-600" />
          <h4 className="font-semibold text-gray-900">Seller Motivation</h4>
        </div>
        <p className="text-lg font-medium text-gray-900">
          {strategy.seller_motivation.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
        </p>
      </div>
    </div>
  );
}

function TalkingPointsList({ talkingPoints }: { talkingPoints: any[] }) {
  if (!talkingPoints || talkingPoints.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="h-5 w-5 text-primary-600" />
        <h4 className="font-semibold text-gray-900">Talking Points & Leverage</h4>
      </div>

      <div className="space-y-4">
        {talkingPoints.map((point, index) => (
          <div key={index} className="border-l-4 border-primary-500 pl-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="font-medium text-gray-900">{point.point}</p>
                <p className="mt-1 text-sm text-gray-600">{point.evidence}</p>
                <span className="inline-block mt-2 text-xs font-medium text-gray-500 uppercase">
                  {point.category.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="ml-4">
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className={`h-2 w-2 rounded-full ${
                        i < Math.round(point.weight * 5) ? 'bg-primary-600' : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1 text-center">Weight</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DealStructureCard({ dealStructure }: { dealStructure: any }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="h-5 w-5 text-primary-600" />
        <h4 className="font-semibold text-gray-900">Recommended Deal Structure</h4>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Contingencies:</p>
          <ul className="space-y-1">
            {dealStructure.contingencies?.map((cont: string, i: number) => (
              <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                {cont.charAt(0).toUpperCase() + cont.slice(1)}
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Inspection Period:</span>
            <span className="text-sm font-medium text-gray-900">
              {dealStructure.inspection_period_days} days
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Closing Timeline:</span>
            <span className="text-sm font-medium text-gray-900">
              {dealStructure.closing_timeline_days} days
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Earnest Money:</span>
            <span className="text-sm font-medium text-gray-900">
              {dealStructure.earnest_money_percent}%
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Escalation Clause:</span>
            <span className="text-sm font-medium text-gray-900">
              {dealStructure.escalation_clause ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function CounterOfferStrategyCard({ counterStrategy }: { counterStrategy: any }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-2 mb-4">
        <Target className="h-5 w-5 text-primary-600" />
        <h4 className="font-semibold text-gray-900">Counter-Offer Strategy</h4>
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-sm font-medium text-gray-700 mb-1">Concession Strategy:</p>
          <p className="text-sm text-gray-600">
            {counterStrategy.concession_strategy?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
          </p>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Alternative Concessions:</p>
          <ul className="space-y-1">
            {counterStrategy.alternative_concessions?.map((conc: string, i: number) => (
              <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-yellow-600" />
                {conc}
              </li>
            ))}
          </ul>
        </div>

        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Max Increase on First Counter:</span>
            <span className="text-sm font-medium text-gray-900">
              {formatCurrency(counterStrategy.initial_counter_max_increase)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function RisksOpportunitiesGrid({ strategy }: { strategy: any }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Risks */}
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <h4 className="font-semibold text-red-900">Key Risks</h4>
        </div>
        {strategy.key_risks && strategy.key_risks.length > 0 ? (
          <ul className="space-y-2">
            {strategy.key_risks.map((risk: string, i: number) => (
              <li key={i} className="text-sm text-red-800 flex items-start gap-2">
                <span className="text-red-400 mt-1">•</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-red-700 italic">None identified</p>
        )}
      </div>

      {/* Opportunities */}
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="h-5 w-5 text-green-600" />
          <h4 className="font-semibold text-green-900">Key Opportunities</h4>
        </div>
        {strategy.key_opportunities && strategy.key_opportunities.length > 0 ? (
          <ul className="space-y-2">
            {strategy.key_opportunities.map((opp: string, i: number) => (
              <li key={i} className="text-sm text-green-800 flex items-start gap-2">
                <span className="text-green-400 mt-1">•</span>
                <span>{opp}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-green-700 italic">None identified</p>
        )}
      </div>
    </div>
  );
}
