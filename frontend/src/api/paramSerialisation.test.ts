import { describe, expect, it } from 'vitest';
import axios from 'axios';
import { REPEATED_KEY_PARAMS } from './client';

// Guards the axios config the API depends on: FastAPI binds ?domain=a&domain=b to a
// list[str], but axios' default array form (?domain[]=a) would make it 422 instead.
describe('REPEATED_KEY_PARAMS', () => {
  const instance = axios.create({ paramsSerializer: REPEATED_KEY_PARAMS });

  it('emits repeated keys for arrays', () => {
    expect(
      instance.getUri({
        url: '/components',
        params: { domain: ['animal_behavior', 'earth_observation'], limit: 10 },
      }),
    ).toBe('/components?domain=animal_behavior&domain=earth_observation&limit=10');
  });

  it('omits the key entirely when the filter is unset', () => {
    expect(instance.getUri({ url: '/components', params: { domain: undefined, limit: 10 } })).toBe(
      '/components?limit=10',
    );
  });
});
