"""Create a real, text-based sample PDF for manual testing of the PDF workflow.

Usage:
    python apps/api/scripts/make_sample_pdf.py [output_path]

The generated file has two pages of definition-rich lecture notes, which is the
kind of content the summarizer and the quiz generator work best with.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

PAGE_ONE = """Operating Systems Unit 1 Lecture Notes

An operating system is system software that manages hardware resources and provides
common services for computer programs. The kernel is the core component of an operating
system that stays resident in memory and handles every request from applications. A
process is a program in execution together with its own address space and register state.
A thread is the smallest unit of execution inside a process that shares the process memory.
Context switching is the mechanism of saving the state of one process and loading the state
of another so that the CPU can serve several programs. The process control block is a data
structure that stores the state, registers, and scheduling information of a process.

CPU scheduling is the activity of deciding which ready process receives the processor next.
First come first served is a non preemptive scheduling algorithm that runs processes in the
order in which they arrive in the ready queue. Round robin is a preemptive scheduling
algorithm that gives every process a fixed time slice called a quantum. A deadlock is a
situation in which a set of processes waits forever because each one holds a resource that
another process needs. Mutual exclusion is the property that only one process may use a
shared resource at any instant.
"""

PAGE_TWO = """Operating Systems Unit 1 Memory and Files

Virtual memory is a memory management technique that gives each process the illusion of a
large contiguous main memory. Paging is a memory management scheme that divides memory into
fixed size blocks called frames and pages. A page fault is an interrupt raised when a program
accesses a page that is not currently present in physical memory. Thrashing is the condition
in which the system spends more time swapping pages than executing instructions. Segmentation
is a memory management scheme that divides a program into logical blocks of different sizes.

A system call is the programming interface through which an application requests a service
from the kernel. A file system is the method and data structure that an operating system uses
to keep track of files on a disk. An inode is a data structure that stores the metadata of a
file such as its size, owner, and block locations. A device driver is a program that lets the
operating system communicate with a specific hardware device. Spooling is the technique of
buffering jobs for a device such as a printer so that programs do not wait for slow hardware.
"""


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "sample-operating-systems-unit1.pdf")
    document = pymupdf.open()
    for text in (PAGE_ONE, PAGE_TWO):
        page = document.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 545, 780), text.strip(), fontsize=10.5)
    document.save(target)
    document.close()
    print(f"Wrote {target.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
