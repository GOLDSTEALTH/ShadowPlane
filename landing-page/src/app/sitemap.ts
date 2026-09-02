import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://shadowplane.vercel.app',
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    {
      url: 'https://shadowplane.vercel.app/dashboard/webhooks',
      lastModified: new Date(),
      changeFrequency: 'always',
      priority: 0.8,
    }
  ]
}
