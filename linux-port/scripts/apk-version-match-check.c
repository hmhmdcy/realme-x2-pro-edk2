/*
 * Build a tiny harness against apk-tools' version.c to check dependency
 * matching without installing apk or touching a repository.
 *
 * Usage (from an apk-tools checkout):
 *   gcc -O0 -D_GNU_SOURCE -I src -o verchk \
 *       <this file> src/version.c src/blob.c src/crypto.c
 */

#include <stdio.h>

#include "apk_blob.h"
#include "apk_version.h"

static void check(const char *pkg, const char *op, const char *dep)
{
	int mask = apk_version_result_mask(op);
	int cmp = apk_version_compare(APK_BLOB_STR(pkg), APK_BLOB_STR(dep));
	int match = apk_version_match(APK_BLOB_STR(pkg), mask, APK_BLOB_STR(dep));

	printf("%-16s %-3s %-16s cmp=%-3s match=%s\n", pkg, op, dep,
	       apk_version_op_string(cmp), match ? "YES" : "NO");
}

int main(void)
{
	/* Same version, different revision: "~" must accept, "=" must not. */
	check("99990.7.2-r33", "~", "99990.7.2");
	check("99990.7.2-r40", "~", "99990.7.2");
	check("99990.7.2-r33", "=", "99990.7.2-r33");
	check("99990.7.2-r40", "=", "99990.7.2-r33");

	/* The next major release must be rejected, otherwise the pin is lost. */
	check("99990.8.0-r1", "~", "99990.7.2");
	check("99990.8.0-r1", ">=", "99990.7.2");

	/* A revision-qualified fuzzy pin is no better than an exact pin. */
	check("99990.7.2-r40", "~", "99990.7.2-r33");

	/*
	 * Solver view: with both candidates available, only the 0.7.2 one may
	 * satisfy the fuzzy pin.  A "~" that also accepted 0.8.0 would be
	 * indistinguishable from ">=" for our purposes.
	 */
	{
		const char *candidates[] = { "99990.7.2-r33", "99990.8.0-r1" };
		for (int i = 0; i < 2; i++)
			check(candidates[i], "~", "99990.7.2");
	}

	return 0;
}
