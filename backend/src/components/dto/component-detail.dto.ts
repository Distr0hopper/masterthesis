import { ApiProperty } from "@nestjs/swagger";
import { ComponentDomain, ComponentSource, VALID_DOMAINS } from "../enums";
import { ParameterDto } from "./parameter.dto";

export class ComponentCreatorDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    email: string;

    @ApiProperty({ nullable: true })
    firstName: string | null;

    @ApiProperty({ nullable: true })
    lastName: string | null;
}

export class ComponentDetailDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    name: string;

    @ApiProperty({ nullable: true })
    authorName: string | null;

    @ApiProperty({ type: () => ComponentCreatorDto, nullable: true })
    createdBy: ComponentCreatorDto | null;

    @ApiProperty({ nullable: true })
    description: string | null;

    @ApiProperty({ nullable: true })
    repoUrl: string | null;

    @ApiProperty({ nullable: true })
    repoCommitSha: string | null;

    @ApiProperty({ nullable: true })
    doi: string | null;

    @ApiProperty()
    version: number;

    @ApiProperty()
    cwlContent: string;

    @ApiProperty({ enum: VALID_DOMAINS })
    domain: ComponentDomain;

    @ApiProperty({ enum: ComponentSource })
    source: ComponentSource;

    @ApiProperty({ type: () => [ParameterDto] })
    parameters: ParameterDto[];

    @ApiProperty()
    createdAt: Date;
}