"""Helpers that build real PDFs for the API tests (PyMuPDF is a runtime dependency)."""
from __future__ import annotations

import pymupdf

# Definition-rich study material, the kind a student would upload as lecture notes.
OPERATING_SYSTEMS_TEXT = """Operating Systems Unit 1 Lecture Notes

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

ALGORITHMS_TEXT = """Data Structures and Algorithms Unit 2 Notes

A binary search tree is a node based data structure in which every node has at most two
children and the left subtree holds only smaller keys. A heap is a complete binary tree that
satisfies the heap ordering property for every parent child pair. A hash table is a data
structure that maps keys to positions in an array using a hash function. A collision is the
situation in which a hash function produces the same index for two different keys. Graph
traversal is the process of visiting every vertex of a graph exactly once in a systematic
order. Dijkstra algorithm is a greedy method that finds the shortest path from a source vertex
to every other vertex in a weighted graph. Dynamic programming is a technique that solves a
problem by combining the solutions of overlapping subproblems and storing their results.
A greedy algorithm is a method that makes the locally optimal choice at every stage. Time
complexity is a function that describes how the running time of an algorithm grows with the
size of its input. Space complexity is the amount of memory an algorithm needs relative to the
size of its input. Amortized analysis is the technique of averaging the cost of an operation
over a whole sequence of operations. A spanning tree is a subgraph that connects all the
vertices of a graph without forming any cycle. Recursion is a technique in which a function
calls itself on a smaller instance of the same problem.
"""


def make_pdf(*page_texts: str) -> bytes:
    """Build a real, text-based PDF from the given page contents."""
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        page.insert_textbox(
            pymupdf.Rect(50, 50, 545, 780),
            text.strip(),
            fontsize=10.5,
            align=0,
        )
    data = document.tobytes()
    document.close()
    return data


def make_blank_pdf(pages: int = 2) -> bytes:
    """A structurally valid PDF with no text layer at all."""
    document = pymupdf.open()
    for _ in range(pages):
        document.new_page()
    data = document.tobytes()
    document.close()
    return data


def make_scanned_pdf() -> bytes:
    """A page that only contains an image, i.e. no extractable text."""
    document = pymupdf.open()
    page = document.new_page()
    image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 60))
    image.clear_with(120)
    page.insert_image(pymupdf.Rect(72, 72, 300, 200), pixmap=image)
    data = document.tobytes()
    document.close()
    return data


def make_tiny_pdf(text: str) -> bytes:
    """A PDF with too little text to summarise or build a quiz from."""
    return make_pdf(text)
