import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useApiQuery<T>(key: string[], fn: () => Promise<T>, options?: { enabled?: boolean; refetchInterval?: number }) {
  return useQuery({ queryKey: key, queryFn: fn, ...options });
}

export function useApiMutation<T, V>(
  fn: (variables: V) => Promise<T>,
  options?: { onSuccess?: () => void; invalidateKeys?: string[][] }
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      options?.invalidateKeys?.forEach(key => queryClient.invalidateQueries({ queryKey: key }));
      options?.onSuccess?.();
    },
  });
}
