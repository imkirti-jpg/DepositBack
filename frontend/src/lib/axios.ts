import { create } from 'axios';

import { env } from '@/config/env';

export const apiClient = create({
  baseURL: env.apiBaseUrl,
  timeout: 15_000,
});
