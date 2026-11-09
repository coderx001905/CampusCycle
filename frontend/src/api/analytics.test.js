import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import apiClient from './client.js';
import { analyticsApi } from './analytics.js';

describe('Analytics API Client Module', () => {
  let originalGet;

  beforeEach(() => {
    originalGet = apiClient.get;
  });

  afterEach(() => {
    apiClient.get = originalGet;
  });

  test('getSummary invokes GET /analytics/summary', async () => {
    let capturedUrl = null;
    apiClient.get = async (url) => {
      capturedUrl = url;
      return {
        data: {
          success: true,
          data: {
            scope: 'college',
            college_id: 1,
            verification_status: 'verified',
            colleges: null,
            resources: {
              total_listings: 5,
              active_listings: 4,
              inactive_listings: 1,
              depleted_listings: 0,
              total_quantity: 20,
              available_quantity: 15,
              reserved_quantity: 5,
            },
            requests: {
              total_requests: 10,
              pending_requests: 2,
              approved_requests: 3,
              rejected_requests: 0,
              in_progress_requests: 0,
              awaiting_resolution_requests: 0,
              completed_requests: 5,
              cancelled_requests: 0,
              incoming_requests: 6,
              outgoing_requests: 4,
            },
            transfers: {
              total_transfers: 3,
              preparing_transfers: 1,
              dispatched_transfers: 1,
              partially_received_transfers: 0,
              disputed_transfers: 0,
              received_transfers: 0,
              completed_transfers: 1,
              cancellation_pending_transfers: 0,
              cancelled_transfers: 0,
              outbound_transfers: 2,
              inbound_transfers: 1,
            },
          },
        },
      };
    };

    const result = await analyticsApi.getSummary();
    assert.equal(capturedUrl, '/analytics/summary');
    assert.equal(result.success, true);
    assert.equal(result.data.resources.total_listings, 5);
    assert.equal(result.data.resources.available_quantity, 15);
    assert.equal(result.data.requests.pending_requests, 2);
    assert.equal(result.data.transfers.total_transfers, 3);
  });

  test('getCategories invokes GET /analytics/categories with strict backend contract', async () => {
    let capturedUrl = null;
    apiClient.get = async (url) => {
      capturedUrl = url;
      return {
        data: {
          success: true,
          data: {
            scope: 'college',
            college_id: 1,
            items: [
              {
                category: 'Textbooks',
                total_listings: 3,
                active_listings: 3,
                total_quantity: 15,
                available_quantity: 12,
                reserved_quantity: 3,
              },
            ],
            total_categories: 1,
          },
        },
      };
    };

    const result = await analyticsApi.getCategories();
    assert.equal(capturedUrl, '/analytics/categories');
    assert.equal(result.success, true);
    assert.equal(result.data.items.length, 1);
    assert.equal(result.data.items[0].category, 'Textbooks');
    assert.equal(result.data.items[0].total_listings, 3);
    assert.equal(result.data.items[0].active_listings, 3);
  });

  test('getRequests invokes GET /analytics/requests with by_status and by_type', async () => {
    let capturedUrl = null;
    apiClient.get = async (url) => {
      capturedUrl = url;
      return {
        data: {
          success: true,
          data: {
            scope: 'college',
            college_id: 1,
            total_requests: 4,
            by_status: [{ status: 'completed', count: 4 }],
            by_type: [{ request_type: 'donation', count: 4, quantity: 20 }],
            total_requested_quantity: 20,
            total_approved_quantity: 20,
            fulfillment_rate: 100.0,
            sent_count: 2,
            received_count: 2,
          },
        },
      };
    };

    const result = await analyticsApi.getRequests();
    assert.equal(capturedUrl, '/analytics/requests');
    assert.equal(result.success, true);
    assert.equal(result.data.total_requests, 4);
    assert.equal(result.data.fulfillment_rate, 100.0);
    assert.equal(result.data.by_status[0].status, 'completed');
    assert.equal(result.data.by_status[0].count, 4);
    assert.equal(result.data.by_type[0].request_type, 'donation');
    assert.equal(result.data.by_type[0].count, 4);
  });

  test('getTransfers invokes GET /analytics/transfers with quantity_metrics and dispute_metrics', async () => {
    let capturedUrl = null;
    apiClient.get = async (url) => {
      capturedUrl = url;
      return {
        data: {
          success: true,
          data: {
            scope: 'college',
            college_id: 1,
            total_transfers: 2,
            by_status: [{ status: 'dispatched', count: 2, quantity: 10 }],
            by_leg: [{ leg: 'requested_resource', count: 2, quantity: 10 }],
            dispute_metrics: {
              total_disputed: 1,
              open_disputes: 1,
              resolved_disputes: 0,
              outcomes: {},
            },
            quantity_metrics: {
              total_shipped: 10,
              received_good: 7,
              damaged: 2,
              missing: 1,
            },
            outbound_count: 2,
            inbound_count: 0,
          },
        },
      };
    };

    const result = await analyticsApi.getTransfers();
    assert.equal(capturedUrl, '/analytics/transfers');
    assert.equal(result.success, true);
    assert.equal(result.data.by_status[0].status, 'dispatched');
    assert.equal(result.data.quantity_metrics.total_shipped, 10);
    assert.equal(result.data.quantity_metrics.received_good, 7);
    assert.equal(result.data.quantity_metrics.damaged, 2);
    assert.equal(result.data.quantity_metrics.missing, 1);
    assert.equal(result.data.dispute_metrics.open_disputes, 1);
    assert.equal(result.data.dispute_metrics.resolved_disputes, 0);
  });

  test('getColleges invokes GET /analytics/colleges with top_participating_colleges using id and name', async () => {
    let capturedUrl = null;
    apiClient.get = async (url) => {
      capturedUrl = url;
      return {
        data: {
          success: true,
          data: {
            total_colleges: 3,
            verified_colleges: 2,
            pending_colleges: 1,
            rejected_colleges: 0,
            colleges_with_active_listings: 2,
            colleges_with_completed_transfers: 1,
            top_participating_colleges: [
              {
                id: 1,
                name: 'Alpha College',
                city: 'Metro City',
                verification_status: 'verified',
                active_listings_count: 10,
                completed_transfers_count: 5,
              },
            ],
          },
        },
      };
    };

    const result = await analyticsApi.getColleges();
    assert.equal(capturedUrl, '/analytics/colleges');
    assert.equal(result.success, true);
    assert.equal(result.data.total_colleges, 3);
    assert.equal(result.data.top_participating_colleges[0].id, 1);
    assert.equal(result.data.top_participating_colleges[0].name, 'Alpha College');
    assert.equal(result.data.top_participating_colleges[0].active_listings_count, 10);
    assert.equal(result.data.top_participating_colleges[0].completed_transfers_count, 5);
  });

  test('propagates errors rejected by apiClient', async () => {
    apiClient.get = async () => {
      const err = new Error('Forbidden');
      err.response = { status: 403, data: { detail: 'Only platform administrators may view college analytics' } };
      throw err;
    };

    await assert.rejects(
      async () => {
        await analyticsApi.getColleges();
      },
      (err) => {
        assert.equal(err.response.status, 403);
        assert.equal(err.response.data.detail, 'Only platform administrators may view college analytics');
        return true;
      }
    );
  });
});
