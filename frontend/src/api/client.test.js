import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  getAccessToken,
  setAccessToken,
  clearAccessToken,
  getCookie,
  apiClient,
} from './client.js';

describe('API Client & Authentication Infrastructure', () => {
  beforeEach(() => {
    clearAccessToken();
    // Setup a mock document.cookie
    globalThis.document = {
      cookie: '',
    };
  });

  test('manages access token strictly in memory', () => {
    assert.equal(getAccessToken(), null, 'Initial access token must be null');

    setAccessToken('sample-jwt-token-12345');
    assert.equal(getAccessToken(), 'sample-jwt-token-12345', 'Access token should match set value');

    clearAccessToken();
    assert.equal(getAccessToken(), null, 'Access token must be null after clearing');
  });

  test('extracts specific cookies accurately from document.cookie', () => {
    globalThis.document.cookie = 'theme=dark; campuscycle_csrf=csrf-secret-token-abc; other=val';

    const csrf = getCookie('campuscycle_csrf');
    assert.equal(csrf, 'csrf-secret-token-abc');

    const theme = getCookie('theme');
    assert.equal(theme, 'dark');

    const nonExistent = getCookie('non_existent');
    assert.equal(nonExistent, null);
  });

  test('request interceptor injects Authorization header when token is in memory', async () => {
    setAccessToken('valid-bearer-token');

    // Simulate request interceptor handler
    const interceptor = apiClient.interceptors.request.handlers[0].fulfilled;
    const config = {
      headers: {},
      url: '/resources',
    };

    const updatedConfig = await interceptor(config);
    assert.equal(updatedConfig.headers.Authorization, 'Bearer valid-bearer-token');
  });

  test('request interceptor injects X-CSRF-Token header on /auth/refresh and /auth/logout', async () => {
    globalThis.document.cookie = 'campuscycle_csrf=csrf-test-val-987';

    const interceptor = apiClient.interceptors.request.handlers[0].fulfilled;

    // Test on refresh
    const refreshConfig = {
      headers: {},
      url: '/auth/refresh',
    };
    const updatedRefresh = await interceptor(refreshConfig);
    assert.equal(updatedRefresh.headers['X-CSRF-Token'], 'csrf-test-val-987');

    // Test on logout
    const logoutConfig = {
      headers: {},
      url: '/auth/logout',
    };
    const updatedLogout = await interceptor(logoutConfig);
    assert.equal(updatedLogout.headers['X-CSRF-Token'], 'csrf-test-val-987');

    // Test on regular endpoint (must NOT inject CSRF token)
    const normalConfig = {
      headers: {},
      url: '/resources',
    };
    const updatedNormal = await interceptor(normalConfig);
    assert.equal(updatedNormal.headers['X-CSRF-Token'], undefined);
  });

  test('base client uses configured withCredentials and content type', () => {
    assert.equal(apiClient.defaults.withCredentials, true, 'withCredentials must be true for HttpOnly cookies');
    assert.equal(apiClient.defaults.headers['Content-Type'], 'application/json');
  });

  test('response interceptor ignores 401 on login or register without triggering refresh loop', async () => {
    const errorInterceptor = apiClient.interceptors.response.handlers[0].rejected;

    const loginError = {
      response: { status: 401 },
      config: { url: '/auth/login' },
    };

    await assert.rejects(
      async () => errorInterceptor(loginError),
      (err) => err === loginError,
      'Login 401 must reject directly without attempting refresh'
    );

    const registerError = {
      response: { status: 401 },
      config: { url: '/auth/register' },
    };

    await assert.rejects(
      async () => errorInterceptor(registerError),
      (err) => err === registerError,
      'Register 401 must reject directly without attempting refresh'
    );
  });

  test('response interceptor ignores 401 on refresh endpoint to avoid infinite loops', async () => {
    const errorInterceptor = apiClient.interceptors.response.handlers[0].rejected;

    const refreshError = {
      response: { status: 401 },
      config: { url: '/auth/refresh' },
    };

    await assert.rejects(
      async () => errorInterceptor(refreshError),
      (err) => err === refreshError,
      'Refresh 401 must reject directly'
    );
  });
});
