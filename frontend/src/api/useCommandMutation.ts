import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';

/**
 * A mutation that invalidates one entity's whole query key on success.
 *
 * Every `/commands` call shares that exact cache behaviour - a command can flip an
 * entity's status, its links, or its membership in a list, so nothing narrower than the
 * entity root is safe to invalidate. Keeping it here means a newly added command hook
 * cannot forget it.
 *
 * Deliberately returns the plain `UseMutationResult` rather than a pre-bound helper
 * object: each command hook below stays an ordinary react-query hook, so call sites keep
 * using `mutate(vars, { onSuccess, onError })` as they do for every other mutation.
 */
export function useCommandMutation<TVars, TData>(queryKey: QueryKey, mutationFn: (vars: TVars) => Promise<TData>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
