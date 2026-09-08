// Stable import surface; response contracts are generated from backend OpenAPI.
export type * from './api-types';
export type { Tone } from './tone';
export type ValueKind = import('./api-types').StatCardView['value_kind'];
/** ISO-8601 date serialized by Pydantic. */
export type IsoDate = string;
