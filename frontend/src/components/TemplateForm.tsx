'use client'

import { useState, useEffect } from 'react'
import { X, Save, Eye, FileText, Mail, MessageSquare } from 'lucide-react'

interface TemplateFormData {
  name: string
  description: string
  template_type: 'email' | 'sms' | 'letter' | 'voicemail'
  category: 'initial_outreach' | 'follow_up' | 'negotiation' | 'closing' | 'maintenance' | 'other'
  subject: string
  body: string
  tags: string[]
}

interface TemplateFormProps {
  mode: 'create' | 'edit'
  initialData?: Partial<TemplateFormData> & { id?: string }
  onSubmit: (data: TemplateFormData) => Promise<void>
  onCancel: () => void
}

const TEMPLATE_TYPES = [
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'sms', label: 'SMS', icon: MessageSquare },
  { value: 'letter', label: 'Letter', icon: FileText },
  { value: 'voicemail', label: 'Voicemail', icon: FileText },
]

const CATEGORIES = [
  { value: 'initial_outreach', label: 'Initial Outreach' },
  { value: 'follow_up', label: 'Follow Up' },
  { value: 'negotiation', label: 'Negotiation' },
  { value: 'closing', label: 'Closing' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'other', label: 'Other' },
]

const COMMON_VARIABLES = [
  '{{owner_name}}',
  '{{property_address}}',
  '{{city}}',
  '{{sender_name}}',
  '{{sender_phone}}',
  '{{sender_email}}',
  '{{offer_amount}}',
  '{{closing_days}}',
]

export default function TemplateForm({
  mode,
  initialData,
  onSubmit,
  onCancel,
}: TemplateFormProps) {
  const [formData, setFormData] = useState<TemplateFormData>({
    name: initialData?.name || '',
    description: initialData?.description || '',
    template_type: initialData?.template_type || 'email',
    category: initialData?.category || 'initial_outreach',
    subject: initialData?.subject || '',
    body: initialData?.body || '',
    tags: initialData?.tags || [],
  })

  const [tagInput, setTagInput] = useState('')
  const [preview, setPreview] = useState(false)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Template name is required'
    }

    if (!formData.body.trim()) {
      newErrors.body = 'Template body is required'
    }

    if (formData.template_type === 'email' && !formData.subject.trim()) {
      newErrors.subject = 'Subject line is required for email templates'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) {
      return
    }

    try {
      setSaving(true)
      await onSubmit(formData)
    } catch (error) {
      console.error('Failed to save template:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData({
        ...formData,
        tags: [...formData.tags, tagInput.trim()],
      })
      setTagInput('')
    }
  }

  const handleRemoveTag = (tag: string) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter((t) => t !== tag),
    })
  }

  const insertVariable = (variable: string) => {
    setFormData({
      ...formData,
      body: formData.body + variable,
    })
  }

  const SelectedIcon = TEMPLATE_TYPES.find(
    (t) => t.value === formData.template_type
  )?.icon || FileText

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {mode === 'create' ? 'Create New Template' : 'Edit Template'}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Use {'{{variable}}'} placeholders for dynamic content
            </p>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Template Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Template Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                  errors.name ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="e.g., Initial Outreach - Off Market"
              />
              {errors.name && (
                <p className="text-sm text-red-600 mt-1">{errors.name}</p>
              )}
            </div>

            {/* Template Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Template Type <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {TEMPLATE_TYPES.map((type) => {
                  const Icon = type.icon
                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() =>
                        setFormData({
                          ...formData,
                          template_type: type.value as any,
                        })
                      }
                      className={`flex items-center justify-center space-x-2 px-4 py-2 border rounded-lg transition-colors ${
                        formData.template_type === type.value
                          ? 'bg-primary-50 border-primary-500 text-primary-700'
                          : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      <span className="text-sm font-medium">{type.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Category & Description */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                value={formData.category}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    category: e.target.value as any,
                  })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tags
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddTag()
                    }
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Add tag..."
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Add
                </button>
              </div>
              {formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center space-x-1 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                    >
                      <span>{tag}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="hover:text-blue-900"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="Brief description of when to use this template"
            />
          </div>

          {/* Subject (for email only) */}
          {formData.template_type === 'email' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject Line <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) =>
                  setFormData({ ...formData, subject: e.target.value })
                }
                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                  errors.subject ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="Interest in your property at {{property_address}}"
              />
              {errors.subject && (
                <p className="text-sm text-red-600 mt-1">{errors.subject}</p>
              )}
            </div>
          )}

          {/* Body */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Message Body <span className="text-red-500">*</span>
              </label>
              <button
                type="button"
                onClick={() => setPreview(!preview)}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center space-x-1"
              >
                <Eye className="h-4 w-4" />
                <span>{preview ? 'Edit' : 'Preview'}</span>
              </button>
            </div>
            <textarea
              value={formData.body}
              onChange={(e) =>
                setFormData({ ...formData, body: e.target.value })
              }
              rows={12}
              className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm ${
                errors.body ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="Hi {{owner_name}},&#10;&#10;My name is {{sender_name}}..."
            />
            {errors.body && (
              <p className="text-sm text-red-600 mt-1">{errors.body}</p>
            )}
          </div>

          {/* Common Variables */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Common Variables
            </label>
            <div className="flex flex-wrap gap-2">
              {COMMON_VARIABLES.map((variable) => (
                <button
                  key={variable}
                  type="button"
                  onClick={() => insertVariable(variable)}
                  className="text-xs font-mono bg-gray-100 text-gray-700 px-2 py-1 rounded hover:bg-gray-200 transition-colors"
                >
                  {variable}
                </button>
              ))}
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4" />
              <span>{saving ? 'Saving...' : mode === 'create' ? 'Create Template' : 'Save Changes'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
