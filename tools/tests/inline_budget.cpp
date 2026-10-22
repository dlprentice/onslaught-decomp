// inline_budget.cpp: VC6 spends its per-function inline budget from the end of the function, so the earliest call
// sites are the ones left out of line.
//
// Compile it with the pinned toolchain and flags (copy it into src/ under a scratch name, build it with
// tools/decomp.py's build(), and disassemble F1). With INLINE_BUDGET_TAIL 18 the loop's First() is inlined; with
// 19 both First() calls in the loop become calls to GenericSPtrSet::First (retail's COMDAT 00406d20). Each Size()
// counts two expansions (SPtrSet<T>::Size, then GenericSPtrSet::Size) although neither produces code. (Dead code
// still counts: an `if (0)` around the calls does not remove them from the budget, so this file uses #if.)
//
// Retail shows the same effect: UPhysicsManager::Reload (00510800) calls First out of line in its first loop over
// UBattleEngineDataManager's set and inlines it in the second loop over the same set, and ~CUnitData (005110f0)
// calls it out of line in its early loops.
#include "common.h"
#include "SPtrSet.h"

#ifndef INLINE_BUDGET_TAIL
#define INLINE_BUDGET_TAIL 19
#endif

class D { public: ~D(); int x; };
extern SPtrSet<D> SETD;
extern SPtrSet<int> SETS[40];

void F1()
{
	D *d;
	while (d = SETD.First())
	{
		SETD.Remove(d);
		delete d;
	}
#if INLINE_BUDGET_TAIL > 0
	SETS[0].Size();
#endif
#if INLINE_BUDGET_TAIL > 1
	SETS[1].Size();
#endif
#if INLINE_BUDGET_TAIL > 2
	SETS[2].Size();
#endif
#if INLINE_BUDGET_TAIL > 3
	SETS[3].Size();
#endif
#if INLINE_BUDGET_TAIL > 4
	SETS[4].Size();
#endif
#if INLINE_BUDGET_TAIL > 5
	SETS[5].Size();
#endif
#if INLINE_BUDGET_TAIL > 6
	SETS[6].Size();
#endif
#if INLINE_BUDGET_TAIL > 7
	SETS[7].Size();
#endif
#if INLINE_BUDGET_TAIL > 8
	SETS[8].Size();
#endif
#if INLINE_BUDGET_TAIL > 9
	SETS[9].Size();
#endif
#if INLINE_BUDGET_TAIL > 10
	SETS[10].Size();
#endif
#if INLINE_BUDGET_TAIL > 11
	SETS[11].Size();
#endif
#if INLINE_BUDGET_TAIL > 12
	SETS[12].Size();
#endif
#if INLINE_BUDGET_TAIL > 13
	SETS[13].Size();
#endif
#if INLINE_BUDGET_TAIL > 14
	SETS[14].Size();
#endif
#if INLINE_BUDGET_TAIL > 15
	SETS[15].Size();
#endif
#if INLINE_BUDGET_TAIL > 16
	SETS[16].Size();
#endif
#if INLINE_BUDGET_TAIL > 17
	SETS[17].Size();
#endif
#if INLINE_BUDGET_TAIL > 18
	SETS[18].Size();
#endif
#if INLINE_BUDGET_TAIL > 19
	SETS[19].Size();
#endif
#if INLINE_BUDGET_TAIL > 20
	SETS[20].Size();
#endif
#if INLINE_BUDGET_TAIL > 21
	SETS[21].Size();
#endif
#if INLINE_BUDGET_TAIL > 22
	SETS[22].Size();
#endif
#if INLINE_BUDGET_TAIL > 23
	SETS[23].Size();
#endif
}
