# OpenTDP (FIN TDP)

OpenTDP — also known as FIN TDP — is an open specification for Technical Data Packages (TDPs). It exists to solve a problem the industry has lived with for years: TDPs are constantly referenced, but rarely defined in a way that's concrete enough to implement. OpenTDP replaces that ambiguity with a practical, extensible structure that can grow alongside the needs of the communities using it.

At its core, a TDP file works like a manufacturing recipe — it bundles all the technical information needed to produce a part using advanced manufacturing methods, including additive manufacturing (3D printing). By standardizing how that information is packaged, OpenTDP helps keep critical spare parts available, strengthens supply-chain resilience, supports more sustainable manufacturing practices, and enables the adoption of distributed manufacturing concepts.

Specifically, OpenTDP defines:
- the TDP file structure
- the metadata schema
- the tooling ecosystem needed for interoperable technical data exchange across organizations, systems, and manufacturing environments

## Why OpenTDP?

The push for a well-defined TDP format comes straight from end users. Organizations working with advanced manufacturing have consistently pointed out that existing TDP concepts are too abstract and too hard to put into practice.

Technical Data Packages show up throughout manufacturing standards, defense documentation, and industrial workflows — yet the term "TDP" is routinely criticized for being:

- Too abstract
- Inconsistently defined
- Lacking a common structure
- Not interoperable across tools or organizations

OpenTDP is the community-driven answer to that: an open, clearly defined, extensible specification that anyone can adopt, improve, and implement together.

## File Structure

An OpenTDP package consists of:

- An XML file containing structured metadata, technical definitions, and quality/IPR information
- Associated attachment files (e.g., CAD models, simulation data, process parameters, certificates)
- A ZIP-based container that bundles everything together
- The file extension `.tdp`

This keeps OpenTDP both human-readable and machine-processable, and makes it straightforward to integrate into existing PLM, CAD, and manufacturing systems.

## Goals

- Enable advanced manufacturing
- Ensure spare-part availability
- Improve supply-chain resilience
- Support sustainability
- Enable the adoption of distributed manufacturing
- Enable IPR and quality compliance

## What OpenTDP Provides

- A structured TDP file format
- Tools for creating and reading TDPs
- An extensible ecosystem

## License

OpenTDP is licensed under the GNU General Public License v3.0 (GPLv3).
See the LICENSE file for details.
