export type CompanyService = { name: string; category: string; description: string };

export type ProfileQualityIssue = {
  field: string;
  severity: string;
  code: string;
  message: string;
  current_value?: string;
};

export type CompanyFields = {
  name: string;
  website: string;
  description: string;
  industry: string;
  company_size: string;
  country: string;
  city: string;
  timezone: string;
  contact_email: string;
  countries_served: string[];
  target_customers: string[];
  target_industries: string[];
  specialties: string[];
  positioning: string;
  products_services: CompanyService[];
};

export type CompanyProfile = CompanyFields & {
  organization_id: string;
  version: string | null;
  can_edit: boolean;
  onboarding_status: string;
  quality_issues?: ProfileQualityIssue[];
};

export const companyFieldLabels: Record<keyof CompanyFields, string> = {
  name: 'Company name',
  website: 'Company website',
  description: 'Company description',
  industry: 'Industry',
  company_size: 'Company size',
  country: 'Headquarters country',
  city: 'Headquarters city',
  timezone: 'Company timezone',
  contact_email: 'Public business contact email',
  countries_served: 'Countries served',
  target_customers: 'Target customers',
  target_industries: 'Target industries',
  specialties: 'Specialties',
  positioning: 'Business positioning',
  products_services: 'Products and services',
};

export function companyDraft(profile: CompanyProfile): CompanyFields {
  return {
    name: profile.name,
    website: profile.website,
    description: profile.description,
    industry: profile.industry,
    company_size: profile.company_size,
    country: profile.country,
    city: profile.city,
    timezone: profile.timezone,
    contact_email: profile.contact_email,
    countries_served: profile.countries_served || [],
    target_customers: profile.target_customers || [],
    target_industries: profile.target_industries || [],
    specialties: profile.specialties || [],
    positioning: profile.positioning || '',
    products_services: profile.products_services || [],
  };
}
