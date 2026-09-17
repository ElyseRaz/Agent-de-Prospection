import { useQuery } from "@tanstack/react-query";
import { getJob, searchJobs } from "../api/jobs";
import type { JobSearchFilters } from "../api/types";

export function useJobSearch(filters: JobSearchFilters) {
  return useQuery({
    queryKey: ["jobs", "search", filters],
    queryFn: () => searchJobs(filters),
    placeholderData: (previous) => previous,
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => getJob(jobId as string),
    enabled: Boolean(jobId),
  });
}
