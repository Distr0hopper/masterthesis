import { z } from 'zod';

export const repoUrlSchema = z.url('Invalid repository URL');
