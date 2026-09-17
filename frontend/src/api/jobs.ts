import { apiFetch } from "./client";
import type { JobDetail, JobSearchFilters, JobSearchResponse } from "./types";

export function searchJobs(filters: JobSearchFilters): Promise<JobSearchResponse> {
  return apiFetch<JobSearchResponse>("/jobs/search", { query: { ...filters } });
}

export function getJob(jobId: string): Promise<JobDetail> {
  return apiFetch<JobDetail>(`/jobs/${jobId}`);
}
